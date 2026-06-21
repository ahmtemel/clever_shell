#include "minishell.h"

/* =========================================================================
** Terminal state
** ========================================================================= */

static struct termios	g_orig_termios;
static struct termios	g_raw_termios;
static int				g_is_raw = 0;

static void	restore_on_exit(void)
{
	if (g_is_raw)
	{
		tcsetattr(STDIN_FILENO, TCSAFLUSH, &g_orig_termios);
		g_is_raw = 0;
	}
}

/*
** Switch STDIN to Non-Canonical / Raw mode:
**   - ECHO off    : we echo manually (needed for Ghost Text later)
**   - ICANON off  : characters arrive one at a time (no line buffering)
**   - ISIG kept   : Ctrl+C/Ctrl+\ still generate signals
** A no-op when stdin is not a terminal.
*/
void	init_raw_mode(void)
{
	if (!isatty(STDIN_FILENO))
		return ;
	if (tcgetattr(STDIN_FILENO, &g_orig_termios) < 0)
		return ;
	g_raw_termios = g_orig_termios;
	g_raw_termios.c_lflag &= ~(ECHO | ICANON);
	g_raw_termios.c_cc[VMIN]  = 1;
	g_raw_termios.c_cc[VTIME] = 0;
	if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &g_raw_termios) < 0)
		return ;
	g_is_raw = 1;
	atexit(restore_on_exit);
}

/* Explicit restore (called before exit() in main). */
void	restore_terminal(void)
{
	restore_on_exit();
}

/*
** Re-apply raw mode after a child process may have altered terminal settings.
** Called by the executor (parent side) immediately after every waitpid so that
** programs which restore canonical mode before exiting (python REPL, vi, etc.)
** cannot leave the shell in an inconsistent state.
** Also fixes the primary bug: exit() in a child triggers atexit handlers which
** call tcsetattr to restore canonical mode — _exit() skips them, but this
** function acts as a second line of defence.
*/
void	reapply_raw_mode(void)
{
	if (!isatty(STDIN_FILENO) || !g_is_raw)
		return ;
	tcsetattr(STDIN_FILENO, TCSAFLUSH, &g_raw_termios);
}

/* =========================================================================
** Command history
** ========================================================================= */

#define HIST_CAP 500

static char	*g_hist[HIST_CAP];
static int	g_hist_len = 0;

/*
** Append line to the history ring.
** Empty lines and consecutive duplicates are skipped.
*/
void	history_add(const char *line)
{
	if (!line || !*line)
		return ;
	if (g_hist_len > 0 && strcmp(g_hist[g_hist_len - 1], line) == 0)
		return ;
	if (g_hist_len == HIST_CAP)
	{
		free(g_hist[0]);
		memmove(g_hist, g_hist + 1, sizeof(char *) * (HIST_CAP - 1));
		g_hist_len--;
	}
	g_hist[g_hist_len] = strdup(line);
	if (g_hist[g_hist_len])
		g_hist_len++;
}

void	history_free(void)
{
	int	i;

	i = 0;
	while (i < g_hist_len)
		free(g_hist[i++]);
	g_hist_len = 0;
}

/* =========================================================================
** Line buffer
** ========================================================================= */

#define LINE_CAP 4096

typedef struct s_lbuf
{
	char	data[LINE_CAP];
	int		len;
	char	saved[LINE_CAP];		/* preserves current edit during history nav  */
	int		hist_pos;				/* -1 = not navigating history                */
	char	prediction[LINE_CAP];	/* adjusted suffix to display as ghost text   */
	char	last_sent[LINE_CAP];	/* buffer content of the most recent ZMQ send */
}	t_lbuf;

/* Erase every visible character (cursor must already be at end). */
static void	lb_erase(t_lbuf *lb)
{
	while (lb->len > 0)
	{
		write(STDOUT_FILENO, "\b \b", 3);
		lb->len--;
	}
}

/* Replace buffer + screen with src string. */
static void	lb_set(t_lbuf *lb, const char *src)
{
	int	i;

	lb_erase(lb);
	i = 0;
	while (src[i] && i < LINE_CAP - 1)
	{
		lb->data[i] = src[i];
		write(STDOUT_FILENO, (const void *)&src[i], 1);
		i++;
	}
	lb->data[i] = '\0';
	lb->len = i;
}

/* =========================================================================
** ANSI escape sequence parser
**
** After reading the leading ESC (\x1b), we switch to VMIN=0 VTIME=1
** (100 ms timeout) to consume the rest of the sequence without blocking
** if the user pressed bare ESC.  Afterwards we restore the normal raw mode.
** ========================================================================= */

#define ESC_NONE  0
#define ESC_UP    1
#define ESC_DOWN  2
#define ESC_RIGHT 3
#define ESC_LEFT  4

static int	parse_escape_seq(void)
{
	struct termios	t;
	unsigned char	seq[8];
	ssize_t			n;

	if (!g_is_raw)
		return (ESC_NONE);
	t = g_raw_termios;
	t.c_cc[VMIN]  = 0;
	t.c_cc[VTIME] = 1;
	tcsetattr(STDIN_FILENO, TCSANOW, &t);
	n = read(STDIN_FILENO, seq, 7);
	tcsetattr(STDIN_FILENO, TCSANOW, &g_raw_termios);
	if (n < 2 || seq[0] != '[')
		return (ESC_NONE);
	if (seq[1] == 'A')
		return (ESC_UP);
	if (seq[1] == 'B')
		return (ESC_DOWN);
	if (seq[1] == 'C')
		return (ESC_RIGHT);
	if (seq[1] == 'D')
		return (ESC_LEFT);
	return (ESC_NONE);
}

/* =========================================================================
** Non-interactive fallback (stdin is a pipe / file)
** ========================================================================= */

static char	*read_line_noterm(void)
{
	char	*line;
	size_t	n;
	ssize_t	len;

	line = NULL;
	n = 0;
	len = getline(&line, &n, stdin);
	if (len < 0)
	{
		free(line);
		return (NULL);
	}
	if (len > 0 && line[len - 1] == '\n')
		line[len - 1] = '\0';
	return (line);
}

/* =========================================================================
** Ghost Text rendering (Phase 5)
**
** The cursor is always kept at the end of the REAL typed text.
** The prediction suffix is rendered to the right of it in dim grey.
**
** ghost_clear : cursor at real-text-end → overwrite grey with spaces →
**               move cursor back left → prediction = "".
** ghost_render: cursor at real-text-end → write grey prediction →
**               move cursor back left (stays at real-text-end).
**
** write_cursor_left: emit ANSI CSI n D (move cursor left by n).
** ========================================================================= */

/*
** Move cursor left n columns via ANSI CSI n D.
** Used exclusively by ghost_render to park the cursor back after writing
** the prediction text to the right.
*/
static void	write_cursor_left(int n)
{
	char	csi[16];
	int		len;

	if (n <= 0)
		return ;
	len = snprintf(csi, sizeof(csi), "\x1b[%dD", n);
	if (len > 0)
		write(STDOUT_FILENO, csi, (size_t)len);
}

/*
** Erase the grey prediction from the screen.
**
** Previous approach (space-overwrite + cursor-left) was fragile: any prior
** cursor drift caused the wrong number of columns to be overwritten, leading
** to ghost text remnants ("gitt status" glitch) or double rendering.
**
** Fix: use ANSI EL (Erase in Line) \x1b[0K — erases from the current cursor
** position to end of line WITHOUT moving the cursor.  Because the cursor is
** always parked at the end of the real typed text (guaranteed by ghost_render),
** this reliably wipes out exactly the grey suffix regardless of its length.
*/
static void	ghost_clear(t_lbuf *lb)
{
	if (lb->prediction[0] == '\0')
		return ;
	write(STDOUT_FILENO, "\x1b[0K", 4);
	lb->prediction[0] = '\0';
}

/*
** Render lb->prediction as dim grey text to the right of the real text.
** Cursor starts and ends at the end of the real typed text.
**
** Sequence:
**   \x1b[90m  – set foreground colour to dark grey (bright black)
**   <prediction text>
**   \x1b[0m   – reset all attributes
**   \x1b[nD   – move cursor left n columns (back to end of real buffer)
*/
static void	ghost_render(t_lbuf *lb)
{
	int	plen;

	plen = (int)strlen(lb->prediction);
	if (plen == 0)
		return ;
	write(STDOUT_FILENO, "\x1b[90m", 5);
	write(STDOUT_FILENO, lb->prediction, (size_t)plen);
	write(STDOUT_FILENO, "\x1b[0m", 4);
	write_cursor_left(plen);
}

/* =========================================================================
** Interactive raw-mode read loop
**
** Handles per-character input with:
**   Enter        : ghost erase → return the accumulated line
**   Ctrl+D       : EOF signal (return NULL if buffer empty)
**   Tab (0x09)   : accept prediction → append to buffer, write in white
**   Backspace    : ghost erase → visual delete → request new prediction
**   Ctrl+C       : SIGINT already delivered → EINTR → return ""
**   ESC [ A/B    : ghost erase → up/down history navigation
**   ESC [ C/D    : silently ignored (Phase 5 scope: end-of-line cursor only)
**   Printable    : ghost erase → echo → request new prediction
** ========================================================================= */

/*
** Validate and adjust the raw prediction received from the daemon.
**
** The daemon replied to last_sent, so the true full completion is:
**   full = last_sent + raw
**
** The current buffer (lb->data) may have grown by one or more characters
** since that send.  The adjusted ghost suffix is:
**   lb->prediction = full[ lb->len : ]
**
** Validity conditions (all must hold):
**   1. full fits in LINE_CAP.
**   2. lb->data starts with last_sent  (buffer only grew, never shrank/changed).
**   3. full starts with lb->data       (completion is consistent with current input).
**
** If any condition fails the prediction is stale (e.g. the user deleted chars
** or the daemon is way behind) and is silently discarded.
** Returns 1 when lb->prediction was set, 0 when discarded.
*/
static int	adjust_prediction(t_lbuf *lb, const char *raw)
{
	char	full[LINE_CAP];
	int		ls_len;
	int		raw_len;
	int		full_len;

	ls_len   = (int)strlen(lb->last_sent);
	raw_len  = (int)strlen(raw);
	full_len = ls_len + raw_len;
	if (full_len >= LINE_CAP)
		return (0);
	if (lb->len < ls_len || memcmp(lb->last_sent, lb->data, (size_t)ls_len) != 0)
		return (0);
	memcpy(full, lb->last_sent, (size_t)ls_len);
	memcpy(full + ls_len, raw, (size_t)raw_len + 1);
	if (full_len < lb->len || memcmp(full, lb->data, (size_t)lb->len) != 0)
		return (0);
	memcpy(lb->prediction, full + lb->len, (size_t)(full_len - lb->len) + 1);
	return (1);
}

/*
** ZMQ update: recv → validate/adjust → render → remember → send.
**
** Order matters:
**   1. Receive FIRST (before updating last_sent) so that last_sent still
**      holds the buffer of the PREVIOUS send, letting adjust_prediction
**      correctly reconstruct the full completion.
**   2. Update last_sent to the CURRENT buffer.
**   3. Send the current buffer (daemon will reply on the NEXT cycle).
**
** This eliminates the off-by-one lag: the ghost shown for buffer "gi" is
** derived from the reply to "g" (last_sent + raw suffix = full completion),
** adjusted to the suffix that extends "gi" – giving the correct "t status"
** instead of the raw (mis-aligned) "it status".
*/
static void	zmq_update(t_lbuf *lb)
{
	char	raw[LINE_CAP];

	lb->prediction[0] = '\0';
	if (zmq_ipc_recv(raw, LINE_CAP) && adjust_prediction(lb, raw))
		ghost_render(lb);
	memcpy(lb->last_sent, lb->data, (size_t)lb->len + 1);
	zmq_ipc_send(lb->data);
}

/*
** Tab: accept the current prediction (if any).
** The grey ghost is erased, the prediction is written in normal colour,
** and appended permanently to the buffer.
*/
static void	tab_accept(t_lbuf *lb)
{
	char	tmp[LINE_CAP];
	int		plen;

	plen = (int)strlen(lb->prediction);
	if (plen == 0 || lb->len + plen >= LINE_CAP)
		return ;
	memcpy(tmp, lb->prediction, (size_t)plen + 1);
	ghost_clear(lb);
	write(STDOUT_FILENO, tmp, (size_t)plen);
	memcpy(lb->data + lb->len, tmp, (size_t)plen + 1);
	lb->len += plen;
	lb->hist_pos = -1;
	zmq_update(lb);
}

static void	handle_escape(t_lbuf *lb)
{
	int	esc;

	esc = parse_escape_seq();
	if (esc == ESC_UP)
	{
		if (g_hist_len == 0)
			return ;
		if (lb->hist_pos == -1)
		{
			memcpy(lb->saved, lb->data, (size_t)lb->len + 1);
			lb->hist_pos = g_hist_len;
		}
		if (lb->hist_pos > 0)
		{
			lb->hist_pos--;
			ghost_clear(lb);
			lb_set(lb, g_hist[lb->hist_pos]);
			zmq_update(lb);
		}
	}
	else if (esc == ESC_DOWN)
	{
		if (lb->hist_pos == -1)
			return ;
		lb->hist_pos++;
		ghost_clear(lb);
		if (lb->hist_pos >= g_hist_len)
		{
			lb->hist_pos = -1;
			lb_set(lb, lb->saved);
		}
		else
			lb_set(lb, g_hist[lb->hist_pos]);
		zmq_update(lb);
	}
}

char	*read_line(const char *prompt)
{
	t_lbuf			lb;
	unsigned char	c;
	ssize_t			n;

	if (!isatty(STDIN_FILENO))
		return (read_line_noterm());
	lb.len            = 0;
	lb.data[0]        = '\0';
	lb.saved[0]       = '\0';
	lb.prediction[0]  = '\0';
	lb.last_sent[0]   = '\0';
	lb.hist_pos       = -1;
	write(STDOUT_FILENO, prompt, strlen(prompt));
	while (1)
	{
		n = read(STDIN_FILENO, &c, 1);
		if (n < 0 && errno == EINTR)
		{
			lb.len = 0;
			lb.data[0] = '\0';
			return (strdup(""));
		}
		if (n <= 0)
		{
			ghost_clear(&lb);
			return (NULL);
		}
		if (c == '\n' || c == '\r')
		{
			ghost_clear(&lb);
			write(STDOUT_FILENO, "\n", 1);
			lb.data[lb.len] = '\0';
			return (strdup(lb.data));
		}
		if (c == '\x04')
		{
			if (lb.len == 0)
			{
				ghost_clear(&lb);
				return (NULL);
			}
			continue ;
		}
		if (c == '\t')
		{
			tab_accept(&lb);
			continue ;
		}
		if (c == '\x7f' || c == '\b')
		{
			if (lb.len > 0)
			{
				ghost_clear(&lb);
				lb.len--;
				lb.data[lb.len] = '\0';
				write(STDOUT_FILENO, "\b \b", 3);
				zmq_update(&lb);
			}
			continue ;
		}
		if (c == '\x1b')
		{
			handle_escape(&lb);
			continue ;
		}
		if (c >= 32 && c < 127)
		{
			if (lb.len < LINE_CAP - 1)
			{
				ghost_clear(&lb);
				lb.data[lb.len++] = (char)c;
				lb.data[lb.len]   = '\0';
				write(STDOUT_FILENO, &c, 1);
				zmq_update(&lb);
			}
			continue ;
		}
	}
}

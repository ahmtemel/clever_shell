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
	char	saved[LINE_CAP];	/* preserves current edit during history nav */
	int		hist_pos;			/* -1 = not navigating history              */
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
** Interactive raw-mode read loop
**
** Handles per-character input with:
**   Enter        : return the accumulated line
**   Ctrl+D       : EOF signal (return NULL if buffer empty)
**   Backspace    : visual delete + buffer pop
**   Ctrl+C       : SIGINT already delivered → EINTR → return ""
**   ESC [ A/B    : up/down history navigation
**   ESC [ C/D    : left/right silently ignored (Phase 5 adds cursor movement)
**   Printable    : echo + buffer append
** ========================================================================= */

char	*read_line(const char *prompt)
{
	t_lbuf			lb;
	unsigned char	c;
	ssize_t			n;
	int				esc;

	if (!isatty(STDIN_FILENO))
		return (read_line_noterm());
	lb.len      = 0;
	lb.data[0]  = '\0';
	lb.saved[0] = '\0';
	lb.hist_pos = -1;
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
			return (NULL);
		if (c == '\n' || c == '\r')
		{
			write(STDOUT_FILENO, "\n", 1);
			lb.data[lb.len] = '\0';
			return (strdup(lb.data));
		}
		if (c == '\x04')
		{
			if (lb.len == 0)
				return (NULL);
			continue ;
		}
		if (c == '\x7f' || c == '\b')
		{
			if (lb.len > 0)
			{
				lb.len--;
				lb.data[lb.len] = '\0';
				write(STDOUT_FILENO, "\b \b", 3);
			}
			continue ;
		}
		if (c == '\x1b')
		{
			esc = parse_escape_seq();
			if (esc == ESC_UP)
			{
				if (g_hist_len == 0)
					continue ;
				if (lb.hist_pos == -1)
				{
					memcpy(lb.saved, lb.data, (size_t)lb.len + 1);
					lb.hist_pos = g_hist_len;
				}
				if (lb.hist_pos > 0)
				{
					lb.hist_pos--;
					lb_set(&lb, g_hist[lb.hist_pos]);
				}
			}
			else if (esc == ESC_DOWN)
			{
				if (lb.hist_pos == -1)
					continue ;
				lb.hist_pos++;
				if (lb.hist_pos >= g_hist_len)
				{
					lb.hist_pos = -1;
					lb_set(&lb, lb.saved);
				}
				else
					lb_set(&lb, g_hist[lb.hist_pos]);
			}
			continue ;
		}
		if (c >= 32 && c < 127)
		{
			if (lb.len < LINE_CAP - 1)
			{
				lb.data[lb.len++] = (char)c;
				lb.data[lb.len]   = '\0';
				write(STDOUT_FILENO, &c, 1);
			}
			continue ;
		}
	}
}

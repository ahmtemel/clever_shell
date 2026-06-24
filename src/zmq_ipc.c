#include "minishell.h"
#include <zmq.h>

/*
** Phase 4 – ZeroMQ IPC layer (C client side).
**
** Pattern : PAIR socket.
**   Python daemon : PAIR, zmq_bind("ipc:///tmp/markov_shell.ipc")
**   C shell       : PAIR, zmq_connect(same address)
**
** All send/recv operations use ZMQ_DONTWAIT (non-blocking).
** EAGAIN means "no data yet" – it is caught and silently ignored so that
** the terminal read loop is NEVER blocked waiting for the AI daemon.
**
** If the daemon is not running, zmq_connect() still succeeds (ZMQ
** connects lazily) and every zmq_recv() simply returns EAGAIN. The shell
** continues to work normally without any prediction.
*/

#define ZMQ_IPC_ADDR "ipc:///tmp/markov_shell.ipc"

static void	*g_zmq_ctx    = NULL;
static void	*g_zmq_socket = NULL;

/*
** Initialise the ZeroMQ context and connect the PAIR socket.
** Called once at shell startup.
** Safe to call even when the daemon is not yet running.
*/
void	zmq_ipc_init(void)
{
	g_zmq_ctx = zmq_ctx_new();
	if (!g_zmq_ctx)
		return ;
	g_zmq_socket = zmq_socket(g_zmq_ctx, ZMQ_PAIR);
	if (!g_zmq_socket)
	{
		zmq_ctx_destroy(g_zmq_ctx);
		g_zmq_ctx = NULL;
		return ;
	}
	/*
	** Set send/recv high-water mark to 1 so that stale predictions are
	** dropped instead of piling up. For a real-time typing assistant,
	** only the latest prediction matters.
	*/
	int	hwm;

	hwm = 1;
	zmq_setsockopt(g_zmq_socket, ZMQ_SNDHWM, &hwm, sizeof(hwm));
	zmq_setsockopt(g_zmq_socket, ZMQ_RCVHWM, &hwm, sizeof(hwm));
	zmq_connect(g_zmq_socket, ZMQ_IPC_ADDR);
}

/*
** Send the current input buffer to the Python daemon (non-blocking).
** Silently ignores EAGAIN (daemon not ready) and any other error.
** buf must be a NUL-terminated string.
*/
void	zmq_ipc_send(const char *buf)
{
	if (!g_zmq_socket || !buf)
		return ;
	zmq_send(g_zmq_socket, buf, strlen(buf), ZMQ_DONTWAIT);
	/* EAGAIN / EFSM / ETERM are all silently ignored */
}

/*
** Try to receive a prediction from the Python daemon (non-blocking).
** Returns 1 and fills 'out' (NUL-terminated) if a message arrived.
** Returns 0 if no message is available (EAGAIN) or on any error.
** 'max' is the size of the 'out' buffer including the NUL terminator.
*/
int	zmq_ipc_recv(char *out, size_t max)
{
	ssize_t	n;

	if (!g_zmq_socket || !out || max == 0)
		return (0);
	n = zmq_recv(g_zmq_socket, out, max - 1, ZMQ_DONTWAIT);
	if (n < 0)
	{
		out[0] = '\0';
		return (0);
	}
	out[n] = '\0';
	return (1);
}

/*
** Poll the socket for up to timeout_ms milliseconds, then recv.
** Returns the byte count (>= 0) and fills 'out' (NUL-terminated) on success.
** Returns -1 if the timeout expires, the socket is not ready, or on error.
** 'max' is the size of 'out' including the NUL terminator.
**
** The poll caps the wait so the terminal loop is never blocked indefinitely.
** A small timeout (10-20 ms) is sufficient; the Markov daemon responds
** in < 1 ms.  DONTWAIT is used for the actual recv so that a spurious POLLIN
** wake-up never stalls either.
*/
int	zmq_ipc_recv_timeout(char *out, size_t max, int timeout_ms)
{
	zmq_pollitem_t	items[1];
	int				rc;
	ssize_t			n;

	if (!g_zmq_socket || !out || max == 0)
		return (-1);
	items[0].socket  = g_zmq_socket;
	items[0].fd      = -1;
	items[0].events  = ZMQ_POLLIN;
	items[0].revents = 0;
	rc = zmq_poll(items, 1, timeout_ms);
	if (rc <= 0)
		return (-1);
	n = zmq_recv(g_zmq_socket, out, max - 1, ZMQ_DONTWAIT);
	if (n < 0)
	{
		out[0] = '\0';
		return (-1);
	}
	out[n] = '\0';
	return ((int)n);
}

/*
** Drain all pending messages from the receive queue (non-blocking).
** Discards every queued reply so the next zmq_ipc_send/recv pair
** starts with a clean, aligned state.  Errors are silently ignored.
*/
void	zmq_ipc_drain(void)
{
	char	buf[4096];

	if (!g_zmq_socket)
		return ;
	while (zmq_recv(g_zmq_socket, buf, sizeof(buf) - 1, ZMQ_DONTWAIT) >= 0)
		;
}

/*
** Destroy the socket and context. Called at shell exit.
*/
void	zmq_ipc_cleanup(void)
{
	if (g_zmq_socket)
	{
		zmq_close(g_zmq_socket);
		g_zmq_socket = NULL;
	}
	if (g_zmq_ctx)
	{
		zmq_ctx_destroy(g_zmq_ctx);
		g_zmq_ctx = NULL;
	}
}

#include "minishell.h"

#include <errno.h>
#include <string.h>

#ifdef USE_ZMQ
#include <zmq.h>
#endif

int ai_hook_init(t_ai_hook *hook, const char *endpoint)
{
    if (!hook)
        return (-1);
    hook->enabled = 0;
    hook->zmq_ctx = NULL;
    hook->zmq_sock = NULL;
#ifdef USE_ZMQ
    hook->zmq_ctx = zmq_ctx_new();
    if (!hook->zmq_ctx)
        return (-1);
    hook->zmq_sock = zmq_socket(hook->zmq_ctx, ZMQ_PUSH);
    if (!hook->zmq_sock)
    {
        zmq_ctx_term(hook->zmq_ctx);
        hook->zmq_ctx = NULL;
        return (-1);
    }
    if (zmq_connect(hook->zmq_sock, endpoint) == -1)
    {
        zmq_close(hook->zmq_sock);
        zmq_ctx_term(hook->zmq_ctx);
        hook->zmq_sock = NULL;
        hook->zmq_ctx = NULL;
        return (-1);
    }
    hook->enabled = 1;
#else
    (void)endpoint;
#endif
    return (0);
}

void ai_hook_shutdown(t_ai_hook *hook)
{
    if (!hook)
        return;
#ifdef USE_ZMQ
    if (hook->zmq_sock)
        zmq_close(hook->zmq_sock);
    if (hook->zmq_ctx)
        zmq_ctx_term(hook->zmq_ctx);
#endif
    hook->zmq_sock = NULL;
    hook->zmq_ctx = NULL;
    hook->enabled = 0;
}

int ai_hook_try_send(t_ai_hook *hook, const char *buffer)
{
#ifdef USE_ZMQ
    int rc;

    if (!hook || !hook->enabled || !buffer)
        return (0);
    rc = zmq_send(hook->zmq_sock, buffer, strlen(buffer), ZMQ_DONTWAIT);
    if (rc == -1 && (errno == EAGAIN || errno == EWOULDBLOCK))
        return (1);
    if (rc == -1)
        return (-1);
    return (0);
#else
    (void)hook;
    (void)buffer;
    return (0);
#endif
}

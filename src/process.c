#include "minishell.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

volatile sig_atomic_t g_sigint_received = 0;

static void sigint_parent_handler(int signo)
{
    (void)signo;
    g_sigint_received = 1;
    write(STDOUT_FILENO, "\n", 1);
}

static int set_sigaction_wrap(int signo, void (*handler)(int), int flags)
{
    struct sigaction sa;

    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = handler;
    sa.sa_flags = flags;
    sigemptyset(&sa.sa_mask);
    return (sigaction(signo, &sa, NULL));
}

int setup_parent_interactive_signals(void)
{
    if (set_sigaction_wrap(SIGINT, sigint_parent_handler, SA_RESTART) == -1)
        return (-1);
    if (set_sigaction_wrap(SIGQUIT, SIG_IGN, SA_RESTART) == -1)
        return (-1);
    return (0);
}

static int setup_child_exec_signals(void)
{
    if (set_sigaction_wrap(SIGINT, SIG_DFL, 0) == -1)
        return (-1);
    if (set_sigaction_wrap(SIGQUIT, SIG_DFL, 0) == -1)
        return (-1);
    return (0);
}

static int wait_status_to_exit_code(int status)
{
    if (WIFEXITED(status))
        return (WEXITSTATUS(status));
    if (WIFSIGNALED(status))
        return (128 + WTERMSIG(status));
    return (1);
}

static int wait_child(pid_t pid, int *last_status)
{
    int status;
    pid_t w;

    while (1)
    {
        w = waitpid(pid, &status, 0);
        if (w == -1 && errno == EINTR)
            continue;
        if (w == -1)
            return (-1);
        break;
    }
    *last_status = wait_status_to_exit_code(status);
    if (WIFSIGNALED(status))
    {
        if (WTERMSIG(status) == SIGQUIT)
            write(STDERR_FILENO, "Quit (core dumped)\n", 19);
        else if (WTERMSIG(status) == SIGINT)
            write(STDERR_FILENO, "\n", 1);
    }
    return (0);
}

static int wait_all_children(pid_t *pids, size_t count, int *last_status)
{
    size_t  i;
    int     status;
    pid_t   w;

    i = 0;
    while (i < count)
    {
        while (1)
        {
            w = waitpid(pids[i], &status, 0);
            if (w == -1 && errno == EINTR)
                continue;
            if (w == -1)
                return (-1);
            break;
        }
        if (pids[i] == pids[count - 1])
            *last_status = wait_status_to_exit_code(status);
        i++;
    }
    return (0);
}

static char *get_env_value(char **envp, const char *key)
{
    size_t key_len;
    int i;

    if (!envp || !key)
        return (NULL);
    key_len = strlen(key);
    i = 0;
    while (envp[i])
    {
        if (!strncmp(envp[i], key, key_len) && envp[i][key_len] == '=')
            return (envp[i] + key_len + 1);
        i++;
    }
    return (NULL);
}

static char *join3(const char *a, const char *b, const char *c)
{
    char    *out;
    size_t  la;
    size_t  lb;
    size_t  lc;

    la = strlen(a);
    lb = strlen(b);
    lc = strlen(c);
    out = malloc(la + lb + lc + 1);
    if (!out)
        return (NULL);
    memcpy(out, a, la);
    memcpy(out + la, b, lb);
    memcpy(out + la + lb, c, lc);
    out[la + lb + lc] = '\0';
    return (out);
}

static char *resolve_executable(const char *cmd)
{
    char    *path_env;
    char    *copy;
    char    *dir;
    char    *saveptr;
    char    *candidate;

    if (!cmd || !*cmd)
        return (NULL);
    if (strchr(cmd, '/'))
    {
        if (access(cmd, X_OK) == 0)
            return (strdup(cmd));
        return (NULL);
    }
    path_env = get_env_value(environ, "PATH");
    if (!path_env)
        return (NULL);
    copy = strdup(path_env);
    if (!copy)
        return (NULL);
    dir = strtok_r(copy, ":", &saveptr);
    while (dir)
    {
        candidate = join3(dir, "/", cmd);
        if (!candidate)
        {
            free(copy);
            return (NULL);
        }
        if (access(candidate, X_OK) == 0)
        {
            free(copy);
            return (candidate);
        }
        free(candidate);
        dir = strtok_r(NULL, ":", &saveptr);
    }
    free(copy);
    return (NULL);
}

static int open_redir_target(t_redir *redir)
{
    if (redir->type == TOK_REDIR_IN)
        return (open(redir->target, O_RDONLY));
    if (redir->type == TOK_REDIR_OUT)
        return (open(redir->target, O_WRONLY | O_CREAT | O_TRUNC, 0644));
    if (redir->type == TOK_APPEND)
        return (open(redir->target, O_WRONLY | O_CREAT | O_APPEND, 0644));
    return (-1);
}

static int apply_redirections(t_redir *redirs)
{
    int fd;

    while (redirs)
    {
        fd = open_redir_target(redirs);
        if (fd < 0)
            return (-1);
        if (redirs->type == TOK_REDIR_IN)
        {
            if (dup2(fd, STDIN_FILENO) == -1)
            {
                close(fd);
                return (-1);
            }
        }
        else
        {
            if (dup2(fd, STDOUT_FILENO) == -1)
            {
                close(fd);
                return (-1);
            }
        }
        if (close(fd) == -1)
            return (-1);
        redirs = redirs->next;
    }
    return (0);
}

static int setup_pipe_ends(int prev_read, int pipefd[2], int has_next)
{
    if (prev_read != -1 && dup2(prev_read, STDIN_FILENO) == -1)
        return (-1);
    if (has_next && dup2(pipefd[1], STDOUT_FILENO) == -1)
        return (-1);
    return (0);
}

static void close_pipe_ends(int prev_read, int pipefd[2], int has_next)
{
    if (prev_read != -1)
        close(prev_read);
    if (has_next)
    {
        close(pipefd[0]);
        close(pipefd[1]);
    }
}

static void exec_child_command(t_cmd *cmd, int prev_read,
    int pipefd[2], int has_next, char **envp)
{
    char *exec_path;

    if (setup_child_exec_signals() == -1
        || setup_pipe_ends(prev_read, pipefd, has_next) == -1
        || apply_redirections(cmd->redirs) == -1)
    {
        perror("minishell");
        _exit(1);
    }
    close_pipe_ends(prev_read, pipefd, has_next);
    if (!cmd->argv || !cmd->argv[0])
        _exit(0);
    (void)envp;
    exec_path = resolve_executable(cmd->argv[0]);
    if (!exec_path)
    {
        dprintf(STDERR_FILENO, "minishell: %s: command not found\n", cmd->argv[0]);
        _exit(127);
    }
    execve(exec_path, cmd->argv, environ);
    dprintf(STDERR_FILENO, "minishell: %s: %s\n", exec_path, strerror(errno));
    free(exec_path);
    _exit(errno == ENOENT ? 127 : 126);
}

int execute_pipeline(t_cmd *pipeline, char **envp, int *last_status)
{
    pid_t   pids[256];
    size_t  count;
    int     prev_read;
    int     pipefd[2];
    int     has_next;
    pid_t   pid;

    count = 0;
    prev_read = -1;
    while (pipeline)
    {
        has_next = (pipeline->next != NULL);
        if (has_next && pipe(pipefd) == -1)
            return (-1);
        pid = fork();
        if (pid < 0)
            return (-1);
        if (pid == 0)
            exec_child_command(pipeline, prev_read, pipefd, has_next, envp);
        if (count < 256)
            pids[count++] = pid;
        if (prev_read != -1)
            close(prev_read);
        if (has_next)
        {
            close(pipefd[1]);
            prev_read = pipefd[0];
        }
        else
            prev_read = -1;
        pipeline = pipeline->next;
    }
    if (wait_all_children(pids, count, last_status) == -1)
        return (-1);
    return (0);
}

int run_external_command(char **argv, char **envp, int *last_status)
{
    pid_t   pid;
    char    *exec_path;

    if (!argv || !argv[0] || !last_status)
        return (-1);
    exec_path = resolve_executable(argv[0]);
    if (!exec_path)
    {
        dprintf(STDERR_FILENO, "minishell: %s: command not found\n", argv[0]);
        *last_status = 127;
        return (0);
    }
    pid = fork();
    if (pid < 0)
    {
        perror("minishell: fork");
        free(exec_path);
        return (-1);
    }
    if (pid == 0)
    {
        if (setup_child_exec_signals() == -1)
        {
            perror("minishell: sigaction");
            free(exec_path);
            _exit(1);
        }
        (void)envp;
        execve(exec_path, argv, environ);
        dprintf(STDERR_FILENO, "minishell: %s: %s\n", exec_path, strerror(errno));
        free(exec_path);
        _exit(errno == ENOENT ? 127 : 126);
    }
    free(exec_path);
    if (wait_child(pid, last_status) == -1)
    {
        perror("minishell: waitpid");
        return (-1);
    }
    return (0);
}

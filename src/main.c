#include "minishell.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define PROMPT "mini$ "
#define AI_ENDPOINT "tcp://127.0.0.1:5557"

static void trim_newline(char *line)
{
    size_t len;

    if (!line)
        return;
    len = strlen(line);
    if (len > 0 && line[len - 1] == '\n')
        line[len - 1] = '\0';
}

static void send_buffer_prefixes(t_ai_hook *hook, const char *line)
{
    char    *tmp;
    size_t   i;
    size_t   len;

    if (!line)
        return;
    len = strlen(line);
    tmp = malloc(len + 1);
    if (!tmp)
        return;
    i = 0;
    while (i < len)
    {
        tmp[i] = line[i];
        tmp[i + 1] = '\0';
        ai_hook_try_send(hook, tmp);
        i++;
    }
    free(tmp);
}

static int run_line(const char *line, char **envp, int *last_status)
{
    t_token *tokens;
    t_cmd   *pipeline;
    char    *err_msg;
    int      should_exit;

    if (!line || !*line)
        return (0);
    if (tokenize_input(line, &tokens, &err_msg) == -1)
    {
        fprintf(stderr, "lexer error: %s\n", err_msg ? err_msg : "unknown");
        free(err_msg);
        *last_status = 2;
        return (-1);
    }
    if (parse_pipeline(tokens, &pipeline, &err_msg) == -1)
    {
        fprintf(stderr, "parser error: %s\n", err_msg ? err_msg : "unknown");
        free(err_msg);
        free_tokens(tokens);
        *last_status = 2;
        return (-1);
    }
    should_exit = 0;
    if (!pipeline->next
        && execute_builtin_if_any(pipeline->argv, last_status, &should_exit))
    {
        free_pipeline(pipeline);
        free_tokens(tokens);
        if (should_exit)
            return (1);
        return (0);
    }
    if (execute_pipeline(pipeline, envp, last_status) == -1)
    {
        perror("minishell: execute_pipeline");
        free_pipeline(pipeline);
        free_tokens(tokens);
        *last_status = 1;
        return (-1);
    }
    free_pipeline(pipeline);
    free_tokens(tokens);
    return (0);
}

int main(int argc, char **argv, char **envp)
{
    char        *line;
    size_t       cap;
    ssize_t      nread;
    int          last_status;
    t_ai_hook    hook;

    (void)argc;
    (void)argv;
    if (setup_parent_interactive_signals() == -1)
    {
        perror("minishell: setup signals");
        return (1);
    }
    if (ai_hook_init(&hook, AI_ENDPOINT) == -1)
    {
        fprintf(stderr, "warning: AI hook disabled (%s)\n", strerror(errno));
        memset(&hook, 0, sizeof(hook));
    }
    line = NULL;
    cap = 0;
    last_status = 0;
    while (1)
    {
        write(STDOUT_FILENO, PROMPT, sizeof(PROMPT) - 1);
        nread = getline(&line, &cap, stdin);
        if (nread == -1)
            break;
        trim_newline(line);
        send_buffer_prefixes(&hook, line);
        if (run_line(line, envp, &last_status) == 1)
            break;
    }
    write(STDOUT_FILENO, "exit\n", 5);
    free(line);
    ai_hook_shutdown(&hook);
    return (last_status);
}

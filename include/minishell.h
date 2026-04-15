#ifndef MINISHELL_H
#define MINISHELL_H

#include <stddef.h>
#include <signal.h>

extern volatile sig_atomic_t g_sigint_received;

typedef enum e_token_type
{
    TOK_WORD,
    TOK_PIPE,
    TOK_REDIR_IN,
    TOK_REDIR_OUT,
    TOK_HEREDOC,
    TOK_APPEND
}   t_token_type;

typedef struct s_token
{
    t_token_type       type;
    char               *value;
    struct s_token     *next;
}   t_token;

typedef struct s_redir
{
    t_token_type       type;
    char               *target;
    struct s_redir     *next;
}   t_redir;

typedef struct s_cmd
{
    char            **argv;
    t_redir          *redirs;
    struct s_cmd     *next;
}   t_cmd;

typedef struct s_ai_hook
{
    void    *zmq_ctx;
    void    *zmq_sock;
    int      enabled;
}   t_ai_hook;

int tokenize_input(const char *input, t_token **out_tokens, char **err_msg);
void free_tokens(t_token *head);
void print_tokens(const t_token *head);

int parse_pipeline(const t_token *tokens, t_cmd **out_pipeline, char **err_msg);
void free_pipeline(t_cmd *pipeline);

int setup_parent_interactive_signals(void);
int run_external_command(char **argv, char **envp, int *last_status);
int execute_pipeline(t_cmd *pipeline, char **envp, int *last_status);
int execute_builtin_if_any(char **argv, int *last_status, int *should_exit);

int ai_hook_init(t_ai_hook *hook, const char *endpoint);
void ai_hook_shutdown(t_ai_hook *hook);
int ai_hook_try_send(t_ai_hook *hook, const char *buffer);

#endif

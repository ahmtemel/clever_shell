#include "minishell.h"

#include <stdlib.h>
#include <string.h>

typedef struct s_vec
{
    char    **data;
    size_t   len;
    size_t   cap;
}   t_vec;

static int set_error(char **err_msg, const char *msg)
{
    *err_msg = strdup(msg);
    if (!*err_msg)
        return (-1);
    return (-1);
}

static void free_strv(char **strv)
{
    size_t i;

    if (!strv)
        return;
    i = 0;
    while (strv[i])
    {
        free(strv[i]);
        i++;
    }
    free(strv);
}

static int vec_init(t_vec *vec)
{
    vec->cap = 4;
    vec->len = 0;
    vec->data = calloc(vec->cap, sizeof(char *));
    if (!vec->data)
        return (-1);
    return (0);
}

static int vec_grow(t_vec *vec)
{
    char    **new_data;
    size_t    new_cap;

    new_cap = vec->cap * 2;
    new_data = realloc(vec->data, new_cap * sizeof(char *));
    if (!new_data)
        return (-1);
    memset(new_data + vec->cap, 0, vec->cap * sizeof(char *));
    vec->data = new_data;
    vec->cap = new_cap;
    return (0);
}

static int vec_push_dup(t_vec *vec, const char *s)
{
    if (vec->len + 2 > vec->cap && vec_grow(vec) == -1)
        return (-1);
    vec->data[vec->len] = strdup(s);
    if (!vec->data[vec->len])
        return (-1);
    vec->len++;
    vec->data[vec->len] = NULL;
    return (0);
}

static char **vec_take(t_vec *vec)
{
    char **out;

    out = vec->data;
    vec->data = NULL;
    vec->len = 0;
    vec->cap = 0;
    return (out);
}

static void vec_free(t_vec *vec)
{
    free_strv(vec->data);
    vec->data = NULL;
    vec->len = 0;
    vec->cap = 0;
}

static void free_redirs(t_redir *redirs)
{
    t_redir *tmp;

    while (redirs)
    {
        tmp = redirs->next;
        free(redirs->target);
        free(redirs);
        redirs = tmp;
    }
}

void free_pipeline(t_cmd *pipeline)
{
    t_cmd *tmp;

    while (pipeline)
    {
        tmp = pipeline->next;
        free_strv(pipeline->argv);
        free_redirs(pipeline->redirs);
        free(pipeline);
        pipeline = tmp;
    }
}

static int add_redir(t_redir **head, t_token_type type, const char *target)
{
    t_redir *redir;
    t_redir *it;

    redir = malloc(sizeof(*redir));
    if (!redir)
        return (-1);
    redir->type = type;
    redir->target = strdup(target);
    if (!redir->target)
    {
        free(redir);
        return (-1);
    }
    redir->next = NULL;
    if (!*head)
    {
        *head = redir;
        return (0);
    }
    it = *head;
    while (it->next)
        it = it->next;
    it->next = redir;
    return (0);
}

static int add_cmd(t_cmd **head, t_cmd **tail, t_vec *argv, t_redir *redirs)
{
    t_cmd *cmd;

    cmd = calloc(1, sizeof(*cmd));
    if (!cmd)
        return (-1);
    cmd->argv = vec_take(argv);
    cmd->redirs = redirs;
    cmd->next = NULL;
    if (!*head)
        *head = cmd;
    else
        (*tail)->next = cmd;
    *tail = cmd;
    return (0);
}

static int finalize_cmd(t_cmd **head, t_cmd **tail, t_vec *argv, t_redir *redirs)
{
    if (argv->len == 0)
        return (-1);
    if (add_cmd(head, tail, argv, redirs) == -1)
        return (-1);
    return (0);
}

int parse_pipeline(const t_token *tokens, t_cmd **out_pipeline, char **err_msg)
{
    t_cmd           *head;
    t_cmd           *tail;
    t_vec            argv;
    t_redir         *redirs;
    t_token_type     redir_type;

    *out_pipeline = NULL;
    *err_msg = NULL;
    head = NULL;
    tail = NULL;
    redirs = NULL;
    if (vec_init(&argv) == -1)
        return (set_error(err_msg, "malloc failed"));
    while (tokens)
    {
        if (tokens->type == TOK_WORD)
        {
            if (vec_push_dup(&argv, tokens->value) == -1)
                break;
            tokens = tokens->next;
            continue;
        }
        if (tokens->type == TOK_REDIR_IN || tokens->type == TOK_REDIR_OUT
            || tokens->type == TOK_APPEND)
        {
            redir_type = tokens->type;
            tokens = tokens->next;
            if (!tokens || tokens->type != TOK_WORD || add_redir(&redirs,
                    redir_type, tokens->value) == -1)
                break;
            tokens = tokens->next;
            continue;
        }
        if (tokens->type == TOK_PIPE)
        {
            if (finalize_cmd(&head, &tail, &argv, redirs) == -1)
                break;
            redirs = NULL;
            if (vec_init(&argv) == -1)
                break;
            tokens = tokens->next;
            continue;
        }
        break;
    }
    if (!tokens && finalize_cmd(&head, &tail, &argv, redirs) == 0)
    {
        *out_pipeline = head;
        return (0);
    }
    vec_free(&argv);
    free_redirs(redirs);
    free_pipeline(head);
    return (set_error(err_msg, "parse error near pipe or redirection"));
}

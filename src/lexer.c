#include "minishell.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct s_sb
{
    char    *buf;
    size_t  len;
    size_t  cap;
}   t_sb;

static int sb_init(t_sb *sb)
{
    sb->cap = 32;
    sb->len = 0;
    sb->buf = malloc(sb->cap);
    if (!sb->buf)
        return (-1);
    sb->buf[0] = '\0';
    return (0);
}

static int sb_grow(t_sb *sb, size_t need)
{
    char    *new_buf;
    size_t  new_cap;

    new_cap = sb->cap;
    while (new_cap < need)
        new_cap *= 2;
    new_buf = realloc(sb->buf, new_cap);
    if (!new_buf)
        return (-1);
    sb->buf = new_buf;
    sb->cap = new_cap;
    return (0);
}

static int sb_push_char(t_sb *sb, char c)
{
    if (sb->len + 2 > sb->cap && sb_grow(sb, sb->len + 2) == -1)
        return (-1);
    sb->buf[sb->len++] = c;
    sb->buf[sb->len] = '\0';
    return (0);
}

static char *sb_take(t_sb *sb)
{
    char *out;

    out = sb->buf;
    sb->buf = NULL;
    sb->len = 0;
    sb->cap = 0;
    return (out);
}

static void sb_free(t_sb *sb)
{
    free(sb->buf);
    sb->buf = NULL;
    sb->len = 0;
    sb->cap = 0;
}

static t_token *token_new(t_token_type type, const char *value)
{
    t_token *token;

    token = malloc(sizeof(*token));
    if (!token)
        return (NULL);
    token->type = type;
    token->value = value ? strdup(value) : NULL;
    if (value && !token->value)
    {
        free(token);
        return (NULL);
    }
    token->next = NULL;
    return (token);
}

static void token_add_back(t_token **head, t_token *new_tok)
{
    t_token *cur;

    if (!*head)
    {
        *head = new_tok;
        return;
    }
    cur = *head;
    while (cur->next)
        cur = cur->next;
    cur->next = new_tok;
}

void free_tokens(t_token *head)
{
    t_token *tmp;

    while (head)
    {
        tmp = head->next;
        free(head->value);
        free(head);
        head = tmp;
    }
}

static int is_op_char(char c)
{
    return (c == '|' || c == '<' || c == '>');
}

static int set_error(char **err_msg, const char *msg)
{
    *err_msg = strdup(msg);
    if (!*err_msg)
        return (-1);
    return (-1);
}

static int read_quoted(const char **p, char quote, t_sb *sb, char **err_msg)
{
    (*p)++;
    while (**p && **p != quote)
    {
        if (sb_push_char(sb, **p) == -1)
            return (set_error(err_msg, "malloc failed"));
        (*p)++;
    }
    if (**p != quote)
        return (set_error(err_msg, "unclosed quote"));
    (*p)++;
    return (0);
}

static int read_word(const char **p, char **out_word, char **err_msg)
{
    t_sb sb;

    if (sb_init(&sb) == -1)
        return (set_error(err_msg, "malloc failed"));
    while (**p && !isspace((unsigned char)**p) && !is_op_char(**p))
    {
        if (**p == '\'' || **p == '"')
        {
            if (read_quoted(p, **p, &sb, err_msg) == -1)
            {
                sb_free(&sb);
                return (-1);
            }
        }
        else
        {
            if (sb_push_char(&sb, **p) == -1)
            {
                sb_free(&sb);
                return (set_error(err_msg, "malloc failed"));
            }
            (*p)++;
        }
    }
    *out_word = sb_take(&sb);
    return (0);
}

static int push_op_token(const char **p, t_token **list)
{
    t_token *tok;

    tok = NULL;
    if (**p == '|')
    {
        tok = token_new(TOK_PIPE, "|");
        (*p)++;
    }
    else if (**p == '<')
    {
        if (*(*p + 1) == '<')
        {
            tok = token_new(TOK_HEREDOC, "<<");
            (*p) += 2;
        }
        else
        {
            tok = token_new(TOK_REDIR_IN, "<");
            (*p)++;
        }
    }
    else if (**p == '>')
    {
        if (*(*p + 1) == '>')
        {
            tok = token_new(TOK_APPEND, ">>");
            (*p) += 2;
        }
        else
        {
            tok = token_new(TOK_REDIR_OUT, ">");
            (*p)++;
        }
    }
    if (!tok)
        return (-1);
    token_add_back(list, tok);
    return (0);
}

int tokenize_input(const char *input, t_token **out_tokens, char **err_msg)
{
    const char  *p;
    t_token     *list;
    t_token     *tok;
    char        *word;

    if (!input || !out_tokens || !err_msg)
        return (-1);
    p = input;
    list = NULL;
    *out_tokens = NULL;
    *err_msg = NULL;
    while (*p)
    {
        while (*p && isspace((unsigned char)*p))
            p++;
        if (!*p)
            break;
        if (is_op_char(*p))
        {
            if (push_op_token(&p, &list) == -1)
            {
                free_tokens(list);
                return (set_error(err_msg, "malloc failed"));
            }
            continue;
        }
        if (read_word(&p, &word, err_msg) == -1)
        {
            free_tokens(list);
            return (-1);
        }
        tok = token_new(TOK_WORD, word);
        free(word);
        if (!tok)
        {
            free_tokens(list);
            return (set_error(err_msg, "malloc failed"));
        }
        token_add_back(&list, tok);
    }
    *out_tokens = list;
    return (0);
}

void print_tokens(const t_token *head)
{
    const char *name;

    while (head)
    {
        name = "WORD";
        if (head->type == TOK_PIPE)
            name = "PIPE";
        else if (head->type == TOK_REDIR_IN)
            name = "REDIR_IN";
        else if (head->type == TOK_REDIR_OUT)
            name = "REDIR_OUT";
        else if (head->type == TOK_HEREDOC)
            name = "HEREDOC";
        else if (head->type == TOK_APPEND)
            name = "APPEND";
        printf("[%s] value='%s'\n", name, head->value ? head->value : "");
        head = head->next;
    }
}

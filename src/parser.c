#include "minishell.h"

static t_ast_node	*new_node(t_ast_type type)
{
	t_ast_node	*node;

	node = malloc(sizeof(t_ast_node));
	if (!node)
		return (NULL);
	node->type = type;
	node->args = NULL;
	node->redirects = NULL;
	node->left = NULL;
	node->right = NULL;
	return (node);
}

static t_redirect	*new_redirect(t_token_type type, char *file)
{
	t_redirect	*redir;

	redir = malloc(sizeof(t_redirect));
	if (!redir)
		return (NULL);
	redir->type = type;
	redir->file = file;
	redir->next = NULL;
	return (redir);
}

static int	is_redirect_token(t_token_type type)
{
	return (type == TOKEN_REDIRECT_IN
		|| type == TOKEN_REDIRECT_OUT
		|| type == TOKEN_REDIRECT_APPEND
		|| type == TOKEN_HEREDOC);
}

/*
** Append one argument word to cmd->args (NULL-terminated, heap-allocated).
** Returns 0 on success, -1 on allocation failure.
** On failure cmd->args still points to the old valid array.
*/
static int	cmd_add_arg(t_ast_node *cmd, int *argc, const char *word)
{
	char	**new_args;
	char	*dup;

	dup = strdup(word);
	if (!dup)
		return (-1);
	new_args = realloc(cmd->args, sizeof(char *) * ((size_t)*argc + 2));
	if (!new_args)
	{
		free(dup);
		return (-1);
	}
	cmd->args = new_args;
	cmd->args[*argc] = dup;
	cmd->args[*argc + 1] = NULL;
	(*argc)++;
	return (0);
}

/*
** Append one redirection to cmd->redirects list.
** Returns 0 on success, -1 on failure.
*/
static int	cmd_add_redirect(t_ast_node *cmd, t_token_type rtype, char *file)
{
	t_redirect	*redir;
	t_redirect	*cur;

	redir = new_redirect(rtype, file);
	if (!redir)
		return (-1);
	if (!cmd->redirects)
	{
		cmd->redirects = redir;
		return (0);
	}
	cur = cmd->redirects;
	while (cur->next)
		cur = cur->next;
	cur->next = redir;
	return (0);
}

/*
** Parse a simple command: a sequence of WORD tokens and redirections.
** Stops when the current token is PIPE or the list is exhausted.
** Advances *cur past all consumed tokens.
*/
static t_ast_node	*parse_command(t_token **cur)
{
	t_ast_node		*cmd;
	t_token_type	rtype;
	char			*file;
	int				argc;

	cmd = new_node(AST_CMD);
	if (!cmd)
		return (NULL);
	argc = 0;
	while (*cur && (*cur)->type != TOKEN_PIPE)
	{
		if ((*cur)->type == TOKEN_WORD)
		{
			if (cmd_add_arg(cmd, &argc, (*cur)->value) < 0)
			{
				free_ast(cmd);
				return (NULL);
			}
			*cur = (*cur)->next;
		}
		else if (is_redirect_token((*cur)->type))
		{
			rtype = (*cur)->type;
			*cur = (*cur)->next;
			if (!*cur || (*cur)->type != TOKEN_WORD)
			{
				fprintf(stderr,
					"minishell: syntax error near unexpected redirect\n");
				free_ast(cmd);
				return (NULL);
			}
			file = strdup((*cur)->value);
			if (!file || cmd_add_redirect(cmd, rtype, file) < 0)
			{
				free(file);
				free_ast(cmd);
				return (NULL);
			}
			*cur = (*cur)->next;
		}
		else
			break ;
	}
	return (cmd);
}

/*
** Parse a pipeline: one or more commands separated by PIPE tokens.
** Grammar: pipeline = command ('|' command)*
** Pipe nodes are left-associative and act as root nodes per architecture.
*/
static t_ast_node	*parse_pipeline(t_token **cur)
{
	t_ast_node	*left;
	t_ast_node	*right;
	t_ast_node	*pipe_node;

	left = parse_command(cur);
	if (!left)
		return (NULL);
	while (*cur && (*cur)->type == TOKEN_PIPE)
	{
		*cur = (*cur)->next;
		if (!*cur)
		{
			fprintf(stderr, "minishell: syntax error: expected command after |\n");
			free_ast(left);
			return (NULL);
		}
		right = parse_command(cur);
		if (!right)
		{
			free_ast(left);
			return (NULL);
		}
		pipe_node = new_node(AST_PIPE);
		if (!pipe_node)
		{
			free_ast(left);
			free_ast(right);
			return (NULL);
		}
		pipe_node->left = left;
		pipe_node->right = right;
		left = pipe_node;
	}
	return (left);
}

/*
** Public entry point.  Takes ownership of nothing – token list is NOT freed.
** Returns root AST node, or NULL on parse error / empty input.
*/
t_ast_node	*ft_parse(t_token *tokens)
{
	t_token	*cur;

	if (!tokens)
		return (NULL);
	cur = tokens;
	return (parse_pipeline(&cur));
}

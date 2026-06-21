#include "minishell.h"

/*
** Free the entire token linked list (including value strings).
*/
void	free_tokens(t_token *tok)
{
	t_token	*next;

	while (tok)
	{
		next = tok->next;
		free(tok->value);
		free(tok);
		tok = next;
	}
}

static void	free_redirect_list(t_redirect *redir)
{
	t_redirect	*next;

	while (redir)
	{
		next = redir->next;
		free(redir->file);
		free(redir);
		redir = next;
	}
}

static void	free_args(char **args)
{
	int	i;

	if (!args)
		return ;
	i = 0;
	while (args[i])
		free(args[i++]);
	free(args);
}

/*
** Recursively free an AST node and all its children.
*/
void	free_ast(t_ast_node *node)
{
	if (!node)
		return ;
	if (node->type == AST_PIPE)
	{
		free_ast(node->left);
		free_ast(node->right);
	}
	else
	{
		free_args(node->args);
		free_redirect_list(node->redirects);
	}
	free(node);
}

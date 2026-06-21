#include "minishell.h"

static void	print_indent(int depth)
{
	int	i;

	i = 0;
	while (i < depth)
	{
		printf("  ");
		i++;
	}
}

static const char	*redir_name(t_token_type type)
{
	if (type == TOKEN_REDIRECT_IN)
		return ("<");
	if (type == TOKEN_REDIRECT_OUT)
		return (">");
	if (type == TOKEN_REDIRECT_APPEND)
		return (">>");
	if (type == TOKEN_HEREDOC)
		return ("<<");
	return ("?");
}

static void	print_redirect_list(t_redirect *redir, int depth)
{
	while (redir)
	{
		print_indent(depth + 1);
		printf("REDIRECT [%s] \"%s\"\n", redir_name(redir->type), redir->file);
		redir = redir->next;
	}
}

/*
** Recursively print the AST with indentation.
** depth controls the indentation level (call with depth = 0).
*/
void	print_ast(t_ast_node *node, int depth)
{
	int	i;

	if (!node)
		return ;
	if (node->type == AST_PIPE)
	{
		print_indent(depth);
		printf("[PIPE]\n");
		print_indent(depth);
		printf(" left:\n");
		print_ast(node->left, depth + 1);
		print_indent(depth);
		printf(" right:\n");
		print_ast(node->right, depth + 1);
	}
	else
	{
		print_indent(depth);
		printf("[CMD]");
		i = 0;
		if (node->args)
		{
			while (node->args[i])
			{
				printf(" \"%s\"", node->args[i]);
				i++;
			}
		}
		printf("\n");
		if (node->redirects)
			print_redirect_list(node->redirects, depth);
	}
}

#include "minishell.h"

/*
** Phase 1 – test driver.
** Reads a line with readline, runs it through the lexer and parser,
** prints the resulting AST, then frees all memory.
** Exits cleanly on Ctrl-D (readline returns NULL).
*/

static void	print_tokens(t_token *tok)
{
	int				i;
	const char		*names[] = {
		"WORD", "PIPE", "REDIR_IN", "REDIR_OUT", "APPEND", "HEREDOC"
	};

	i = 0;
	printf("--- Tokens ---\n");
	while (tok)
	{
		printf("  [%d] type=%-9s value=%s\n",
			i++,
			names[tok->type],
			tok->value ? tok->value : "(null)");
		tok = tok->next;
	}
}

int	main(void)
{
	char		*line;
	t_token		*tokens;
	t_ast_node	*ast;

	while (1)
	{
		line = readline("clever_shell> ");
		if (!line)
		{
			printf("\nexit\n");
			break ;
		}
		if (*line == '\0')
		{
			free(line);
			continue ;
		}
		add_history(line);
		tokens = ft_lexer(line);
		free(line);
		if (!tokens)
			continue ;
		print_tokens(tokens);
		ast = ft_parse(tokens);
		free_tokens(tokens);
		if (!ast)
		{
			printf("--- AST: (parse error) ---\n\n");
			continue ;
		}
		printf("--- AST ---\n");
		print_ast(ast, 0);
		printf("---\n\n");
		free_ast(ast);
	}
	clear_history();
	return (0);
}

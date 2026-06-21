#include "minishell.h"

/*
** Phase 2 – fully functional shell loop.
** Reads input with readline, runs it through Lexer → Parser → Executor,
** then frees all temporary memory before the next iteration.
**
** Signal strategy:
**   • rl_catch_signals = 0  : we fully own signal handling (no readline default handlers).
**   • Interactive mode       : SIGINT prints newline + redraws blank prompt.
**   • Execution mode         : SIGINT set to lighter handler; children get SIG_DFL.
**   • After each command     : return to interactive mode handlers.
*/

/*
** Process one raw input line: lex → parse → execute → free.
** Returns 0 to keep the loop running, 1 to stop (unused here, exit handled in builtin).
*/
static void	process_line(char *line)
{
	t_token		*tokens;
	t_ast_node	*ast;

	tokens = ft_lexer(line);
	if (!tokens)
		return ;
	ast = ft_parse(tokens);
	free_tokens(tokens);
	if (!ast)
		return ;
	execute_node(ast);
	free_ast(ast);
}

int	main(void)
{
	char	*line;

	while (1)
	{
		setup_signals_interactive();
		line = readline("clever_shell> ");
		if (g_signal == SIGINT)
		{
			g_signal = 0;
			g_exit_status = 130;
			free(line);
			continue ;
		}
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
		process_line(line);
		free(line);
	}
	clear_history();
	return (g_exit_status);
}

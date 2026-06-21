#include "minishell.h"

/*
** Phase 3 – raw terminal input loop.
** readline is replaced by our own read_line() which operates in
** Non-Canonical (Raw) mode: every keystroke is received immediately,
** ECHO is disabled (we echo manually), and Backspace is handled visually.
**
** Signal strategy (unchanged from Phase 2):
**   Interactive : SIGINT → sigint_interactive (writes "\n") → read() EINTR
**                 → read_line returns "" → main loop clears g_signal.
**   Execution   : SIGINT → lighter handler; children hold SIG_DFL.
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

	init_raw_mode();
	while (1)
	{
		setup_signals_interactive();
		line = read_line("clever_shell> ");
		if (g_signal == SIGINT)
		{
			g_signal = 0;
			g_exit_status = 130;
			free(line);
			continue ;
		}
		if (!line)
		{
			write(STDOUT_FILENO, "\nexit\n", 6);
			break ;
		}
		if (*line == '\0')
		{
			free(line);
			continue ;
		}
		history_add(line);
		process_line(line);
		free(line);
	}
	history_free();
	restore_terminal();
	return (g_exit_status);
}

#include "minishell.h"

volatile sig_atomic_t	g_signal = 0;

/*
** Interactive handler (shell waiting at readline prompt).
** Writes a newline and uses readline helpers to show a blank new prompt.
** rl_catch_signals must be 0 so we fully own signal handling.
*/
static void	sigint_interactive(int sig)
{
	g_signal = sig;
	write(STDOUT_FILENO, "\n", 1);
	rl_on_new_line();
}

/*
** Execution handler (child process is running).
** Just marks the signal; the child (with SIG_DFL) dies on its own.
*/
static void	sigint_execution(int sig)
{
	g_signal = sig;
	write(STDOUT_FILENO, "\n", 1);
}

/*
** Called once at shell startup and again after each command completes.
** SIGINT  -> custom handler (prints newline, redraws blank prompt).
** SIGQUIT -> ignored (shell must not exit on Ctrl+\).
*/
void	setup_signals_interactive(void)
{
	struct sigaction	sa;

	sa.sa_handler = sigint_interactive;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sigaction(SIGINT, &sa, NULL);

	sa.sa_handler = SIG_IGN;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sigaction(SIGQUIT, &sa, NULL);
}

/*
** Called in the shell (parent) while a child is executing.
** Switches SIGINT to the lighter execution handler.
*/
void	setup_signals_execution(void)
{
	struct sigaction	sa;

	sa.sa_handler = sigint_execution;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sigaction(SIGINT, &sa, NULL);

	sa.sa_handler = SIG_IGN;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sigaction(SIGQUIT, &sa, NULL);
}

/*
** Called inside a forked child immediately before execve.
** Resets both signals to SIG_DFL so the child dies normally on Ctrl+C.
*/
void	setup_signals_child(void)
{
	struct sigaction	sa;

	sa.sa_handler = SIG_DFL;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sigaction(SIGINT, &sa, NULL);
	sigaction(SIGQUIT, &sa, NULL);
}

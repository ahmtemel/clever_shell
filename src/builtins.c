#include "minishell.h"

extern char	**environ;

/* =========================================================================
** Individual builtin implementations
** ========================================================================= */

/*
** echo [-n] [args...]
** Prints arguments separated by spaces. Without -n, appends a newline.
*/
static int	builtin_echo(char **args)
{
	int	i;
	int	newline;

	newline = 1;
	i = 1;
	if (args[1] && strcmp(args[1], "-n") == 0)
	{
		newline = 0;
		i = 2;
	}
	while (args[i])
	{
		printf("%s", args[i]);
		if (args[i + 1])
			printf(" ");
		i++;
	}
	if (newline)
		printf("\n");
	return (0);
}

/*
** pwd
** Prints the current working directory.
*/
static int	builtin_pwd(void)
{
	char	buf[PATH_MAX];

	if (!getcwd(buf, PATH_MAX))
	{
		perror("pwd");
		return (1);
	}
	printf("%s\n", buf);
	return (0);
}

/*
** cd [dir]
** Changes the current directory. Uses HOME if no argument is given.
*/
static int	builtin_cd(char **args)
{
	char	*dir;

	if (!args[1] || args[1][0] == '\0')
		dir = getenv("HOME");
	else
		dir = args[1];
	if (!dir)
	{
		fprintf(stderr, "cd: HOME not set\n");
		return (1);
	}
	if (chdir(dir) < 0)
	{
		perror(dir);
		return (1);
	}
	return (0);
}

/*
** env
** Prints all current environment variables.
*/
static int	builtin_env(void)
{
	int	i;

	i = 0;
	while (environ[i])
		printf("%s\n", environ[i++]);
	return (0);
}

/*
** exit [code]
** Terminates the shell with the given exit code (or last exit status).
*/
static int	builtin_exit(char **args)
{
	int	code;

	code = g_exit_status;
	if (args[1])
		code = atoi(args[1]);
	printf("exit\n");
	clear_history();
	exit(code);
}

/* =========================================================================
** Dispatch
** ========================================================================= */

int	is_builtin(const char *name)
{
	if (!name)
		return (0);
	return (strcmp(name, "echo") == 0
		|| strcmp(name, "pwd") == 0
		|| strcmp(name, "cd") == 0
		|| strcmp(name, "env") == 0
		|| strcmp(name, "exit") == 0);
}

/*
** Run the builtin identified by node->args[0].
** Returns the exit status of the builtin.
*/
int	run_builtin(t_ast_node *node)
{
	char	**args;

	args = node->args;
	if (!args || !args[0])
		return (0);
	if (strcmp(args[0], "echo") == 0)
		return (builtin_echo(args));
	if (strcmp(args[0], "pwd") == 0)
		return (builtin_pwd());
	if (strcmp(args[0], "cd") == 0)
		return (builtin_cd(args));
	if (strcmp(args[0], "env") == 0)
		return (builtin_env());
	if (strcmp(args[0], "exit") == 0)
		return (builtin_exit(args));
	return (1);
}

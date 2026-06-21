#include "minishell.h"

extern char	**environ;

int	g_exit_status = 0;

/* =========================================================================
** Path resolution
** ========================================================================= */

static void	free_str_arr(char **arr)
{
	int	i;

	if (!arr)
		return ;
	i = 0;
	while (arr[i])
		free(arr[i++]);
	free(arr);
}

/*
** Split 'str' by ':' into a NULL-terminated array of heap strings.
** Empty tokens (consecutive colons) are skipped.
*/
static char	**split_colon(const char *str)
{
	const char	*p;
	const char	*start;
	char		**arr;
	int			count;
	int			i;

	count = 0;
	p = str;
	while (*p)
	{
		while (*p == ':')
			p++;
		if (*p)
			count++;
		while (*p && *p != ':')
			p++;
	}
	arr = malloc(sizeof(char *) * ((size_t)count + 1));
	if (!arr)
		return (NULL);
	p = str;
	i = 0;
	while (*p)
	{
		while (*p == ':')
			p++;
		if (!*p)
			break ;
		start = p;
		while (*p && *p != ':')
			p++;
		arr[i] = malloc((size_t)(p - start) + 1);
		if (!arr[i])
		{
			arr[i] = NULL;
			free_str_arr(arr);
			return (NULL);
		}
		memcpy(arr[i], start, (size_t)(p - start));
		arr[i][(size_t)(p - start)] = '\0';
		i++;
	}
	arr[i] = NULL;
	return (arr);
}

static char	*join_path(const char *dir, const char *cmd)
{
	size_t	dlen;
	size_t	clen;
	char	*result;

	dlen = strlen(dir);
	clen = strlen(cmd);
	result = malloc(dlen + clen + 2);
	if (!result)
		return (NULL);
	memcpy(result, dir, dlen);
	result[dlen] = '/';
	memcpy(result + dlen + 1, cmd, clen);
	result[dlen + 1 + clen] = '\0';
	return (result);
}

/*
** Find the absolute path of 'cmd' by searching the PATH environment variable.
** If 'cmd' contains '/', tries it directly.
** Returns a heap-allocated string, or NULL if not found.
*/
static char	*find_in_path(const char *cmd)
{
	char	*path_env;
	char	**dirs;
	char	*full;
	int		i;

	if (!cmd || !*cmd)
		return (NULL);
	if (strchr(cmd, '/'))
	{
		if (access(cmd, F_OK) == 0)
			return (strdup(cmd));
		return (NULL);
	}
	path_env = getenv("PATH");
	if (!path_env)
		return (NULL);
	dirs = split_colon(path_env);
	if (!dirs)
		return (NULL);
	full = NULL;
	i = 0;
	while (dirs[i] && !full)
	{
		full = join_path(dirs[i], cmd);
		if (full && access(full, X_OK) != 0)
		{
			free(full);
			full = NULL;
		}
		i++;
	}
	free_str_arr(dirs);
	return (full);
}

/* =========================================================================
** Redirection
** ========================================================================= */

/*
** Read heredoc content from stdin until the delimiter line is matched.
** Returns the read-end fd of a pipe containing the content, or -1 on error.
*/
static int	heredoc_read(const char *delim)
{
	int		pfd[2];
	char	*line;
	size_t	dlen;

	if (pipe(pfd) < 0)
		return (-1);
	dlen = strlen(delim);
	while (1)
	{
		line = read_line("heredoc> ");
		if (!line)
			break ;
		if (strlen(line) == dlen && memcmp(line, delim, dlen) == 0)
		{
			free(line);
			break ;
		}
		write(pfd[1], line, strlen(line));
		write(pfd[1], "\n", 1);
		free(line);
	}
	close(pfd[1]);
	return (pfd[0]);
}

/*
** Apply all redirections in the list.
** Must be called inside a forked child (or standalone builtin).
** Returns 0 on success, -1 on error (prints error message).
*/
static int	apply_redirections(t_redirect *redir)
{
	int	fd;
	int	target;

	while (redir)
	{
		if (redir->type == TOKEN_REDIRECT_IN)
			fd = open(redir->file, O_RDONLY);
		else if (redir->type == TOKEN_REDIRECT_OUT)
			fd = open(redir->file, O_WRONLY | O_CREAT | O_TRUNC, 0644);
		else if (redir->type == TOKEN_REDIRECT_APPEND)
			fd = open(redir->file, O_WRONLY | O_CREAT | O_APPEND, 0644);
		else
			fd = heredoc_read(redir->file);
		if (fd < 0)
		{
			perror(redir->file);
			return (-1);
		}
		if (redir->type == TOKEN_REDIRECT_IN || redir->type == TOKEN_HEREDOC)
			target = STDIN_FILENO;
		else
			target = STDOUT_FILENO;
		if (dup2(fd, target) < 0)
		{
			perror("dup2");
			close(fd);
			return (-1);
		}
		close(fd);
		redir = redir->next;
	}
	return (0);
}

/* =========================================================================
** Update exit status from a completed child's wait-status word
** ========================================================================= */

static void	update_exit_status(int status)
{
	if (WIFSIGNALED(status))
	{
		g_exit_status = 128 + WTERMSIG(status);
		if (WTERMSIG(status) == SIGINT)
			write(STDOUT_FILENO, "\n", 1);
	}
	else
		g_exit_status = WEXITSTATUS(status);
}

/* =========================================================================
** CMD execution
** ========================================================================= */

/*
** Run an external (non-builtin) command.
** Forks a child, sets up its signals and redirections, then execve's.
** Parent waits and updates g_exit_status.
*/
static int	execute_external(t_ast_node *node)
{
	pid_t	pid;
	char	*path;
	int		status;

	path = find_in_path(node->args[0]);
	fflush(NULL);
	pid = fork();
	if (pid < 0)
	{
		perror("fork");
		free(path);
		return (1);
	}
	if (pid == 0)
	{
		setup_signals_child();
		if (apply_redirections(node->redirects) < 0)
			_exit(1);
		if (!path)
		{
			fprintf(stderr, "clever_shell: %s: command not found\n",
				node->args[0]);
			_exit(127);
		}
		execve(path, node->args, environ);
		perror(node->args[0]);
		free(path);
		_exit(126);
	}
	free(path);
	setup_signals_execution();
	waitpid(pid, &status, 0);
	reapply_raw_mode();
	setup_signals_interactive();
	update_exit_status(status);
	return (g_exit_status);
}

/*
** Execute a CMD node.
** Builtins run in the shell process (so cd/exit affect the shell).
** Redirections for builtins are applied temporarily: the original stdin/stdout
** are saved with dup() before applying and restored afterwards so the shell's
** own file descriptors are never permanently altered.
** External commands are forked.
*/
static int	execute_cmd(t_ast_node *node)
{
	int	saved_in;
	int	saved_out;
	int	ret;

	if (!node->args || !node->args[0])
	{
		if (apply_redirections(node->redirects) < 0)
			return (1);
		return (0);
	}
	if (is_builtin(node->args[0]))
	{
		saved_in = dup(STDIN_FILENO);
		saved_out = dup(STDOUT_FILENO);
		if (apply_redirections(node->redirects) < 0)
		{
			close(saved_in);
			close(saved_out);
			return (1);
		}
		ret = run_builtin(node);
		fflush(stdout);
		dup2(saved_in, STDIN_FILENO);
		dup2(saved_out, STDOUT_FILENO);
		close(saved_in);
		close(saved_out);
		g_exit_status = ret;
		return (ret);
	}
	return (execute_external(node));
}

/* =========================================================================
** PIPE execution
** =========================================================================
**
** For a pipeline A | B:
**   - Fork left child  → dup pipe[1] to STDOUT → execute A → exit
**   - Fork right child → dup pipe[0] to STDIN  → execute B → exit
**   - Parent: close both pipe ends, waitpid both children.
**
** Because execute_node is called recursively inside each child, nested
** pipelines (A | B | C) are handled naturally: the left child of the outer
** pipe runs execute_pipe again for the inner A|B subtree.
**
** fd hygiene: every unused copy of each pipe end is closed before any
** long-running work begins, preventing deadlocks caused by the kernel
** keeping the pipe open while a writer still holds it.
** ========================================================================= */

int	execute_node(t_ast_node *node);

static int	execute_pipe(t_ast_node *node)
{
	int		fd[2];
	pid_t	pid_l;
	pid_t	pid_r;
	int		status;

	if (pipe(fd) < 0)
	{
		perror("pipe");
		return (1);
	}
	fflush(NULL);
	pid_l = fork();
	if (pid_l < 0)
	{
		perror("fork");
		close(fd[0]);
		close(fd[1]);
		return (1);
	}
	if (pid_l == 0)
	{
		close(fd[0]);
		if (dup2(fd[1], STDOUT_FILENO) < 0)
			_exit(1);
		close(fd[1]);
		_exit(execute_node(node->left));
	}
	pid_r = fork();
	if (pid_r < 0)
	{
		perror("fork");
		close(fd[0]);
		close(fd[1]);
		waitpid(pid_l, NULL, 0);
		return (1);
	}
	if (pid_r == 0)
	{
		close(fd[1]);
		if (dup2(fd[0], STDIN_FILENO) < 0)
			_exit(1);
		close(fd[0]);
		_exit(execute_node(node->right));
	}
	close(fd[0]);
	close(fd[1]);
	setup_signals_execution();
	waitpid(pid_l, NULL, 0);
	waitpid(pid_r, &status, 0);
	reapply_raw_mode();
	setup_signals_interactive();
	update_exit_status(status);
	return (g_exit_status);
}

/* =========================================================================
** Public entry point
** ========================================================================= */

int	execute_node(t_ast_node *node)
{
	if (!node)
		return (0);
	if (node->type == AST_PIPE)
		return (execute_pipe(node));
	return (execute_cmd(node));
}

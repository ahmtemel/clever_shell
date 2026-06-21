#ifndef MINISHELL_H
# define MINISHELL_H

# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>
# include <fcntl.h>
# include <signal.h>
# include <errno.h>
# include <sys/wait.h>
# include <limits.h>
# include <termios.h>

/* ========================================================================= */
/* Globals (defined in signals.c and executor.c)                             */
/* ========================================================================= */

extern volatile sig_atomic_t	g_signal;
extern int						g_exit_status;

/* ========================================================================= */
/* Token                                                                      */
/* ========================================================================= */

typedef enum e_token_type
{
	TOKEN_WORD,
	TOKEN_PIPE,
	TOKEN_REDIRECT_IN,
	TOKEN_REDIRECT_OUT,
	TOKEN_REDIRECT_APPEND,
	TOKEN_HEREDOC,
}	t_token_type;

typedef struct s_token
{
	t_token_type	type;
	char			*value;
	struct s_token	*next;
}	t_token;

/* ========================================================================= */
/* AST                                                                        */
/* ========================================================================= */

typedef enum e_ast_type
{
	AST_CMD,
	AST_PIPE,
}	t_ast_type;

/*
** Redirection attached to a command node.
** type : TOKEN_REDIRECT_IN | TOKEN_REDIRECT_OUT |
**        TOKEN_REDIRECT_APPEND | TOKEN_HEREDOC
** file : target filename (or heredoc delimiter for HEREDOC)
*/
typedef struct s_redirect
{
	t_token_type		type;
	char				*file;
	struct s_redirect	*next;
}	t_redirect;

/*
** AST_CMD  : args[]  = NULL-terminated argv, redirects = list of t_redirect.
** AST_PIPE : left    = producing sub-tree,   right     = consuming sub-tree.
*/
typedef struct s_ast_node
{
	t_ast_type			type;
	char				**args;
	t_redirect			*redirects;
	struct s_ast_node	*left;
	struct s_ast_node	*right;
}	t_ast_node;

/* ========================================================================= */
/* Prototypes                                                                 */
/* ========================================================================= */

/* lexer.c */
t_token		*ft_lexer(char *line);

/* parser.c */
t_ast_node	*ft_parse(t_token *tokens);

/* free.c */
void		free_tokens(t_token *tok);
void		free_ast(t_ast_node *node);

/* debug.c */
void		print_ast(t_ast_node *node, int depth);

/* input.c */
void		init_raw_mode(void);
void		restore_terminal(void);
void		reapply_raw_mode(void);
char		*read_line(const char *prompt);
void		history_add(const char *line);
void		history_free(void);

/* zmq_ipc.c */
void		zmq_ipc_init(void);
void		zmq_ipc_send(const char *buf);
int			zmq_ipc_recv(char *out, size_t max);
void		zmq_ipc_cleanup(void);

/* signals.c */
void		setup_signals_interactive(void);
void		setup_signals_execution(void);
void		setup_signals_child(void);

/* builtins.c */
int			is_builtin(const char *name);
int			run_builtin(t_ast_node *node);

/* executor.c */
int			execute_node(t_ast_node *node);

#endif

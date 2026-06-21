#include "minishell.h"

static int	is_space(char c)
{
	return (c == ' ' || c == '\t' || c == '\r' || c == '\n');
}

static int	is_operator(char c)
{
	return (c == '|' || c == '<' || c == '>');
}

static t_token	*new_token(t_token_type type, char *value)
{
	t_token	*tok;

	tok = malloc(sizeof(t_token));
	if (!tok)
		return (NULL);
	tok->type = type;
	tok->value = value;
	tok->next = NULL;
	return (tok);
}

static void	append_token(t_token **head, t_token **tail, t_token *tok)
{
	if (!*head)
	{
		*head = tok;
		*tail = tok;
	}
	else
	{
		(*tail)->next = tok;
		*tail = tok;
	}
}

/*
** Collect one WORD token starting at line[*i].
** Single-quoted content is taken literally; double-quoted content is kept
** as-is (expansion happens in Expander, Phase 1 just strips the quotes).
** Advances *i past the last character of the word.
** Returns heap-allocated string, or NULL on unclosed-quote error.
*/
static char	*collect_word(char *line, int *i)
{
	char	buf[4096];
	int		len;
	char	quote;

	len = 0;
	quote = 0;
	while (line[*i]
		&& (quote || (!is_space(line[*i]) && !is_operator(line[*i]))))
	{
		if (len >= 4095)
			break ;
		if (!quote && (line[*i] == '\'' || line[*i] == '"'))
		{
			quote = line[*i];
			(*i)++;
			continue ;
		}
		if (quote && line[*i] == quote)
		{
			quote = 0;
			(*i)++;
			continue ;
		}
		buf[len++] = line[(*i)++];
	}
	if (quote)
	{
		fprintf(stderr, "minishell: syntax error: unclosed quote\n");
		return (NULL);
	}
	buf[len] = '\0';
	return (strdup(buf));
}

/*
** Handle '<' and '<<' operators.
** *i already points one past the first '<'.
*/
static t_token	*lex_less(char *line, int *i)
{
	if (line[*i] == '<')
	{
		(*i)++;
		return (new_token(TOKEN_HEREDOC, NULL));
	}
	return (new_token(TOKEN_REDIRECT_IN, NULL));
}

/*
** Handle '>' and '>>' operators.
** *i already points one past the first '>'.
*/
static t_token	*lex_greater(char *line, int *i)
{
	if (line[*i] == '>')
	{
		(*i)++;
		return (new_token(TOKEN_REDIRECT_APPEND, NULL));
	}
	return (new_token(TOKEN_REDIRECT_OUT, NULL));
}

/*
** Main lexer entry point.
** Returns the head of a t_token linked list, or NULL on error.
** On error all previously allocated tokens are freed before returning NULL.
*/
t_token	*ft_lexer(char *line)
{
	t_token	*head;
	t_token	*tail;
	t_token	*tok;
	char	*word;
	int		i;

	head = NULL;
	tail = NULL;
	i = 0;
	while (line[i])
	{
		while (is_space(line[i]))
			i++;
		if (!line[i])
			break ;
		tok = NULL;
		if (line[i] == '|')
		{
			i++;
			tok = new_token(TOKEN_PIPE, NULL);
		}
		else if (line[i] == '<')
		{
			i++;
			tok = lex_less(line, &i);
		}
		else if (line[i] == '>')
		{
			i++;
			tok = lex_greater(line, &i);
		}
		else
		{
			word = collect_word(line, &i);
			if (!word)
			{
				free_tokens(head);
				return (NULL);
			}
			tok = new_token(TOKEN_WORD, word);
			if (!tok)
				free(word);
		}
		if (!tok)
		{
			free_tokens(head);
			return (NULL);
		}
		append_token(&head, &tail, tok);
	}
	return (head);
}

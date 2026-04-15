NAME = minishell_stub
CC = cc
CFLAGS = -Wall -Wextra -Werror -Iinclude
SRCS = src/main.c src/lexer.c src/process.c src/parser.c src/ai_hook.c src/builtins.c
OBJS = $(SRCS:.c=.o)

ifdef USE_ZMQ
CFLAGS += -DUSE_ZMQ
LDLIBS += -lzmq
endif

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) $(LDLIBS) -o $(NAME)

clean:
	rm -f $(OBJS)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re

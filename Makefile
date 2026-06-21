NAME    = minishell

CC      = gcc
CFLAGS  = -Wall -Wextra -Werror
IFLAGS  = -Iinc

# macOS: prefer Homebrew readline; fall back to system -lreadline
UNAME   := $(shell uname)
ifeq ($(UNAME), Darwin)
    BREW_RL := $(shell brew --prefix readline 2>/dev/null)
    ifneq ($(BREW_RL),)
        IFLAGS  += -I$(BREW_RL)/include
        LDFLAGS  = -L$(BREW_RL)/lib -lreadline
    else
        LDFLAGS  = -lreadline
    endif
else
    LDFLAGS = -lreadline
endif

SRC_DIR = src
OBJ_DIR = obj

SRCS    = $(SRC_DIR)/main.c      \
          $(SRC_DIR)/lexer.c     \
          $(SRC_DIR)/parser.c    \
          $(SRC_DIR)/free.c      \
          $(SRC_DIR)/debug.c     \
          $(SRC_DIR)/signals.c   \
          $(SRC_DIR)/builtins.c  \
          $(SRC_DIR)/executor.c

OBJS    = $(SRCS:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) $(LDFLAGS) -o $(NAME)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(IFLAGS) -c $< -o $@

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re

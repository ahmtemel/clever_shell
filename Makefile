NAME    = minishell

CC      = gcc
CFLAGS  = -Wall -Wextra -Werror
IFLAGS  = -Iinc

# --------------------------------------------------------------------------- #
# ZeroMQ – detected via pkg-config (installed by Homebrew on macOS).          #
# pkg-config emits the correct -I and -L/-l flags for the local installation. #
# --------------------------------------------------------------------------- #
ZMQ_CFLAGS  = $(shell pkg-config --cflags libzmq 2>/dev/null)
ZMQ_LDFLAGS = $(shell pkg-config --libs   libzmq 2>/dev/null)

SRC_DIR = src
OBJ_DIR = obj

SRCS    = $(SRC_DIR)/main.c      \
          $(SRC_DIR)/input.c     \
          $(SRC_DIR)/lexer.c     \
          $(SRC_DIR)/parser.c    \
          $(SRC_DIR)/free.c      \
          $(SRC_DIR)/debug.c     \
          $(SRC_DIR)/signals.c   \
          $(SRC_DIR)/builtins.c  \
          $(SRC_DIR)/executor.c  \
          $(SRC_DIR)/zmq_ipc.c

OBJS    = $(SRCS:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $(NAME) $(ZMQ_LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(IFLAGS) $(ZMQ_CFLAGS) -c $< -o $@

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re

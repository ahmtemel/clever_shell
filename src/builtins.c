#include "minishell.h"

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern char **environ;

static int is_valid_key_char(int c)
{
    return (isalnum(c) || c == '_');
}

static int parse_assignment(const char *arg, char **key, char **value)
{
    const char  *eq;
    size_t       key_len;

    eq = strchr(arg, '=');
    if (!eq)
        return (1);
    key_len = (size_t)(eq - arg);
    if (key_len == 0 || !(isalpha((unsigned char)arg[0]) || arg[0] == '_'))
        return (0);
    while (key_len > 0)
    {
        key_len--;
        if (!is_valid_key_char((unsigned char)arg[key_len]))
            return (0);
    }
    *key = strndup(arg, (size_t)(eq - arg));
    if (!*key)
        return (-1);
    *value = strdup(eq + 1);
    if (!*value)
    {
        free(*key);
        *key = NULL;
        return (-1);
    }
    return (2);
}

static int builtin_export(char **argv)
{
    int     i;
    int     rc;
    char    *key;
    char    *value;

    if (!argv[1])
    {
        i = 0;
        while (environ[i])
        {
            printf("declare -x %s\n", environ[i]);
            i++;
        }
        return (0);
    }
    i = 1;
    while (argv[i])
    {
        key = NULL;
        value = NULL;
        rc = parse_assignment(argv[i], &key, &value);
        if (rc == -1)
            return (1);
        if (rc == 0)
        {
            fprintf(stderr, "minishell: export: `%s': not a valid identifier\n", argv[i]);
            return (1);
        }
        if (rc == 2)
        {
            if (setenv(key, value, 1) == -1)
            {
                free(key);
                free(value);
                return (1);
            }
            free(key);
            free(value);
        }
        i++;
    }
    return (0);
}

static int is_number_string(const char *s)
{
    size_t i;

    i = 0;
    if (!s || !*s)
        return (0);
    if (s[i] == '+' || s[i] == '-')
        i++;
    if (!s[i])
        return (0);
    while (s[i])
    {
        if (!isdigit((unsigned char)s[i]))
            return (0);
        i++;
    }
    return (1);
}

static int parse_exit_code(const char *arg, int *out)
{
    long value;
    char *end;

    if (!is_number_string(arg))
        return (-1);
    value = strtol(arg, &end, 10);
    if (*end != '\0')
        return (-1);
    if ((value == LONG_MIN || value == LONG_MAX) && errno == ERANGE)
        return (-1);
    *out = (unsigned char)value;
    return (0);
}

static int builtin_exit(char **argv, int *last_status, int *should_exit)
{
    int exit_code;

    if (!argv[1])
    {
        *should_exit = 1;
        return (1);
    }
    if (parse_exit_code(argv[1], &exit_code) == -1)
    {
        fprintf(stderr, "minishell: exit: %s: numeric argument required\n", argv[1]);
        *last_status = 2;
        *should_exit = 1;
        return (1);
    }
    if (argv[2])
    {
        fprintf(stderr, "minishell: exit: too many arguments\n");
        *last_status = 1;
        *should_exit = 0;
        return (1);
    }
    *last_status = exit_code;
    *should_exit = 1;
    return (1);
}

int execute_builtin_if_any(char **argv, int *last_status, int *should_exit)
{
    if (!argv || !argv[0] || !last_status || !should_exit)
        return (0);
    *should_exit = 0;
    if (strcmp(argv[0], "export") == 0)
    {
        *last_status = builtin_export(argv);
        return (1);
    }
    if (strcmp(argv[0], "exit") == 0)
        return (builtin_exit(argv, last_status, should_exit));
    return (0);
}

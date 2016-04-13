#include <unistd.h>
#include <stdio.h>
#include <string.h>

void test_function()
{
    printf("*** test_function()\n");
}

int main(int argc, char **argv)
{
    int a = 0;
    int *b = NULL;
    int c=0,d=0,e=0;

    if (argc > 1 && strcmp(argv[1], "sleep") == 0)
    {
        printf("*** Sleeping for 5 seconds\n");
        sleep(5);
    }
    else if (argc > 1 && strcmp(argv[1], "loop") == 0)
    {
        printf("*** Looping forever()\n");
        while(1) {
            c++;
            d+=2;
            e+=3;
        }
        sleep(1);
    }
    else if (argc > 1 && strcmp(argv[1], "function") == 0)
    {
        printf("*** Calling test_function()\n");
        test_function();
    }
    else if (argc > 1 && strcmp(argv[1], "crash") == 0)
    {
        printf("*** Crashing\n");
        a = *b;
    }
    else
    {
        printf("Usage: inferior < sleep | loop | function | crash >\n");
    }

    return 0;
}

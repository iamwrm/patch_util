#include <stdio.h>

int main(int argc, char *argv[]) {
    printf("Hello from C executable!\n");
    printf("Received %d arguments:\n", argc);
    for (int i = 0; i < argc; ++i) {
        printf("  argv[%d]: %s\n", i, argv[i]);
    }
    // Example of using FetchContent dependency (if added in CMakeLists.txt)
    // e.g., if using cJSON:
    // cJSON *json = cJSON_CreateString("value");
    // char *rendered = cJSON_Print(json);
    // printf("Fetched dependency says: %s\n", rendered);
    // free(rendered);
    // cJSON_Delete(json);
    return 0;
}

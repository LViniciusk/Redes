#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>

int main(int argc, char *argv[]) {
    int sockfd, port;
    struct sockaddr_in serv_addr;
    char buffer[26];
    char servidor_ip[INET_ADDRSTRLEN];

    if (argc >= 2) {
        strncpy(servidor_ip, argv[1], INET_ADDRSTRLEN-1);
        servidor_ip[INET_ADDRSTRLEN-1] = '\0';
    } else {
        printf("Digite o IP do servidor: ");
        if (scanf("%15s", servidor_ip) != 1) {
            fprintf(stderr, "Erro ao ler IP.\n");
            exit(EXIT_FAILURE);
        }
    }

    if (argc >= 3) {
        port = atoi(argv[2]);
        if (port <= 0 || port > 65535) {
            fprintf(stderr, "Porta inválida: %s\n", argv[2]);
            exit(EXIT_FAILURE);
        }
    } else {
        printf("Digite a porta do servidor: ");
        if (scanf("%d", &port) != 1 || port <= 0 || port > 65535) {
            fprintf(stderr, "Erro ao ler porta ou porta inválida.\n");
            exit(EXIT_FAILURE);
        }
    }

    if ((sockfd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port   = htons(port);

    if (inet_pton(AF_INET, servidor_ip, &serv_addr.sin_addr) <= 0) {
        fprintf(stderr, "Endereço inválido: %s\n", servidor_ip);
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    if (connect(sockfd, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("connect");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    ssize_t bytes_lidos = read(sockfd, buffer, sizeof(buffer)-1);
    if (bytes_lidos < 0) {
        perror("read");
        close(sockfd);
        exit(EXIT_FAILURE);
    }
    buffer[bytes_lidos] = '\0'; 

    printf("Data e hora recebidas: %s\n", buffer);
    close(sockfd);
    return 0;
}

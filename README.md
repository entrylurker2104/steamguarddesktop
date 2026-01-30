# 🔐 Steam Desktop Authenticator (SDA) - Python

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/UI-PyQt6-darkblue)](https://www.riverbankcomputing.com/software/pyqt/)
[![Steam Support](https://img.shields.io/badge/Steam-Functional_2025-brightgreen)](https://steampowered.com)

Uma implementação moderna, robusta e **totalmente funcional** do Steam Desktop Authenticator escrita em Python. Este projeto foi atualizado para suportar as mudanças recentes no sistema de autenticação da Valve (2024/2025), permitindo a adição de novas contas e gestão completa de confirmações.

---

## ✨ Funcionalidades

- 🛡️ **Autenticação Moderna (2026)**: Suporte ao novo fluxo `IAuthenticationService` para vincular novos autenticadores.
- 📱 **Geração de Códigos 2FA**: Gerador de códigos TOTP em tempo real com barra de sincronização.
- 🤝 **Gestão de Confirmações**: Visualize, aceite ou recuse trocas (trades) e listagens no mercado da comunidade.
- 💾 **Persistência de Sessão**: Armazenamento seguro de tokens de sessão para evitar logins repetitivos.
- 📁 **Importação de .maFile**: Compatibilidade total com arquivos do Steam Desktop Authenticator (C#) original.
- 🎨 **Interface Premium**: UI escura inspirada no design moderno do Steam, construída com PyQt6.

---

## 🚀 Como Começar

### Pré-requisitos

- Python 3.8 ou superior instalado.
- Git (opcional, para clonar o repositório).

### Instalação

1. **Clone o repositório ou baixe os arquivos:**
   ```powershell
   git clone https://github.com/entrylurker2104/steamguarddesktop.git
   cd steamguarddesktop
   ```

2. **Crie e ative um ambiente virtual:**
   ```powershell
   python -m venv .venv
   
   # No Windows:
   .venv\Scripts\activate
   # No Linux/Mac:
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

---

## 🛠️ Uso

### Executar a Aplicação
```powershell
python app.py
```

### Adicionar uma Nova Conta
1. Clique em **"Add Account"**.
2. Insira suas credenciais do Steam.
3. Se solicitado, insira o código recebido via Email ou App (caso já possua um).
4. Siga as instruções para vincular o novo autenticador via SMS/Email.

### Importar Conta Existente
Se você já utiliza o SDA em C# ou possui um arquivo `.maFile`, clique em **"Import .maFile"** e selecione o arquivo correspondente.

---

## 📦 Estrutura do Projeto

- `app.py`: O coração do sistema, interface gráfica e coordenação.
- `modern_auth.py`: Lógica de autenticação seguindo os protocolos mais recentes do Steam.
- `steam_auth_helper.py`: Utilitários para vinculação e gerenciamento de segredos.
- `time_aligner.py`: Sincroniza o relógio local com os servidores do Steam para garantir códigos válidos.
- `accounts_config.json`: Local onde ficam armazenados os dados (encriptados/segredos) das suas contas.

---

## 🛡️ Segurança e Avisos

> [!WARNING]
> **Use por sua conta e risco.** Embora funcional, esta é uma ferramenta de terceiros não oficial da Valve.

- **Backup**: Sempre guarde seu **Revocation Code** (Código de Revogação) em um local seguro. Ele começa com 'R' e é essencial se você perder acesso ao app.
- **Segurança do PC**: Ao usar um autenticador no Desktop, a segurança da sua conta Steam depende inteiramente da segurança do seu computador.
- **Conta**: Não recomendados o uso comercial em larga escala para evitar flags de automação no Steam.

---

## 🛠️ Tecnologias Utilizadas

- **PyQt6**: Interface gráfica rica e responsiva.
- **Requests**: Comunicação com as APIs do Steam.
- **PyCryptodome**: Criptografia necessária para o handshake RSA.
- **Steam[client]**: Biblioteca base para manipulação de IDs e dados do Steam.

---

## 🤝 Contribuições

Sinta-se à vontade para abrir **Issues** ou enviar **Pull Requests**. Todas as contribuições que melhorem a estabilidade e segurança são bem-vindas!

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---
*Desenvolvido com ❤️ para a comunidade Steam.*




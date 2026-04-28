# Guia de Deploy — GateVision

Esse guia explica como deixar o GateVision acessível durante a apresentação
sem pagar nada: frontend hospedado online e backend rodando no notebook.

---

## Arquitetura

```
Navegador
  └─► Vercel / Netlify (frontend estático — index.html, app.js, styles.css)
        └─► Cloudflare Tunnel (URL pública com HTTPS)
              └─► localhost:8000 no seu notebook (FastAPI + YOLO + EasyOCR)
                    └─► Modelo best.pt
  └─► Supabase (banco de dados — já hospedado)
```

---

## PARTE 1 — Publicar o frontend (faça uma vez)

### Opção A: Vercel (recomendado)

1. Crie uma conta em https://vercel.com com a conta do GitHub do grupo.
2. Faça push do repositório para o GitHub (se ainda não fez).
3. No Vercel, clique em **Add New Project** e importe o repositório.
4. Em **Root Directory**, coloque: `front/Projeto-GateVision-main`
5. Clique em **Deploy**. Pronto — o frontend estará em uma URL como
   `https://gate-vision.vercel.app`.

### Opção B: Netlify

1. Crie uma conta em https://netlify.com.
2. Arraste a pasta `front/Projeto-GateVision-main` direto no site do Netlify
   (Deploy tab → arraste a pasta).
3. Pronto, sem precisar do GitHub.

---

## PARTE 2 — Instalar o Cloudflare Tunnel (faça uma vez)

### Windows

Baixe o executável direto:
https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

Renomeie para `cloudflared.exe` e coloque em uma pasta que você lembre,
por exemplo `C:\Users\SeuUsuario\cloudflared.exe`.

Ou instale via Winget:
```powershell
winget install Cloudflare.cloudflared
```

---

## PARTE 3 — Rotina do dia da apresentação

### Passo 1: Iniciar o backend

Abra um terminal PowerShell e rode:

```powershell
cd C:\caminho\para\Gate-Vision\backend
.\start.bat
```

Aguarde a mensagem: `Modelos carregados com sucesso.`
Teste no navegador: http://localhost:8000
Deve aparecer: `{"status":"ok","service":"GateVision API"}`

### Passo 2: Abrir o Cloudflare Tunnel

Abra **outro** terminal (deixe o backend rodando no primeiro) e rode:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Aguarde alguns segundos. O terminal vai mostrar algo como:

```
2026-04-28T... INF  +----------------------------------------------------------+
2026-04-28T... INF  |  Your quick Tunnel has been created! Visit it at          |
2026-04-28T... INF  |  https://exemplo-alguma-coisa.trycloudflare.com           |
2026-04-28T... INF  +----------------------------------------------------------+
```

Copie essa URL (ex: `https://exemplo-alguma-coisa.trycloudflare.com`).

### Passo 3: Conectar o frontend ao backend

Abra o frontend publicado adicionando `?backend=` com a URL do tunnel:

```
https://gate-vision.vercel.app/?backend=https://exemplo-alguma-coisa.trycloudflare.com
```

O frontend vai salvar essa URL no navegador. Nas próximas aberturas não
precisa mais do `?backend=`, a não ser que o tunnel mude (reiniciar gera
URL nova).

Você verá no topo da interface um chip verde mostrando a URL do backend ativo.

---

## PARTE 4 — Trocar a URL do backend sem reabrir

Se o tunnel reiniciar e gerar uma URL nova:

**Opção 1 (mais fácil):** Clique no chip verde no canto superior direito
da interface — abrirá uma caixa para você colar a nova URL.

**Opção 2:** Abra o frontend com o parâmetro `?backend=` novamente.

**Opção 3:** Edite `config.js` com a nova URL e recarregue a página.
(Só funciona se o localStorage não tiver valor salvo.)

---

## PARTE 5 — Checklist antes de apresentar

- [ ] Backend iniciado e respondendo em http://localhost:8000
- [ ] Cloudflare Tunnel ativo e URL copiada
- [ ] Frontend aberto com `?backend=` apontando para o tunnel
- [ ] Chip no topo mostra a URL do tunnel (verde)
- [ ] Login funcionando (Supabase)
- [ ] Upload de foto com detecção de placa funcionando
- [ ] Webcam funcionando (precisa de HTTPS — Vercel/Netlify já resolve)
- [ ] Dashboard com gráficos carregando
- [ ] Notebook no carregador e sem modo sleep ativo

---

## Dicas importantes

- **Não feche nenhum dos dois terminais** (backend e tunnel) durante a apresentação.
- Deixe o notebook no carregador e desative o modo de espera (Control Panel →
  Power Options → nunca dormir enquanto plugado).
- Se a rede Wi-Fi mudar, o tunnel cai. Gere uma URL nova.
- A webcam só funciona em HTTPS. Sites no Vercel/Netlify já usam HTTPS.
- Se quiser testar tudo localmente antes de hospedar, abra
  `front/Projeto-GateVision-main/index.html` com um servidor local
  (ex: `npx serve .`) em vez de abrir o arquivo direto, pois a webcam
  pode ser bloqueada em `file://`.

---

## Estrutura dos arquivos do frontend

```
front/Projeto-GateVision-main/
├── index.html      # página principal
├── styles.css      # estilos
├── app.js          # lógica do sistema
└── config.js       # configuração opcional do backend (edite a URL aqui)
```

Para alterar a URL do backend diretamente no código, edite `config.js`:

```js
window.GATEVISION_BACKEND_URL = "https://sua-url.trycloudflare.com"
```

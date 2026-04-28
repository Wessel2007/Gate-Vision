// ─────────────────────────────────────────────────────────────────
//  config.js — configuração opcional do backend
//
//  Como usar:
//    1. Edite a variável abaixo com a URL gerada pelo Cloudflare Tunnel.
//    2. Salve o arquivo e recarregue o navegador.
//
//  Este arquivo tem MENOR prioridade que:
//    - o parâmetro ?backend= na URL do navegador
//    - o valor salvo no localStorage (definido pelo chip na barra do topo)
//
//  Para apagar a URL salva no localStorage e forçar o uso deste arquivo,
//  abra o console do navegador e execute:
//    localStorage.removeItem("gv_backend_url")
//
//  Deixe como string vazia ("") para usar http://localhost:8000 como fallback.
// ─────────────────────────────────────────────────────────────────

window.GATEVISION_BACKEND_URL = ""

// Exemplo de uso com Cloudflare Tunnel:
// window.GATEVISION_BACKEND_URL = "https://algum-nome.trycloudflare.com"

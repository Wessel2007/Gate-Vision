import { useState } from "react";

export default function LoginScreen({ onLogin }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!login.trim() || !password.trim()) {
      setError("Preencha usuario e senha.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await onLogin(login.trim(), password.trim());
    } catch (submitError) {
      setError(submitError.message || "Erro ao conectar. Verifique sua conexao.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <div>
          <div className="eyebrow">Controle inteligente de acesso</div>
          <h1 className="logo-title">Vision<em>Gate</em></h1>
          <p className="login-sub">Sistema de acesso por leitura de placa</p>
        </div>
        {error ? <div className="error">{error}</div> : null}
        <div>
          <label htmlFor="loginUsuario" className="login-sub">Usuario</label>
          <input id="loginUsuario" className="input" value={login} onChange={(event) => setLogin(event.target.value)} placeholder="Digite o usuario" />
        </div>
        <div>
          <label htmlFor="loginSenha" className="login-sub">Senha</label>
          <input id="loginSenha" type="password" className="input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Digite a senha" />
        </div>
        <button className="btn primary" type="submit" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </section>
  );
}

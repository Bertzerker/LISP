#!/usr/bin/python3
"""Reproducible LAN login/base-path patch for the pinned official Bracket source."""
import pathlib,sys
root=pathlib.Path(sys.argv[1]);src=root/'frontend/src'
def patch(path,old,new):
    p=pathlib.Path(path);s=p.read_text(encoding='utf8')
    if new in s:return
    if old not in s:raise RuntimeError('Upstream source changed: '+str(p))
    p.write_text(s.replace(old,new),encoding='utf8')
patch(src/'main.tsx','<BrowserRouter>','<BrowserRouter basename="/bracket">')
patch(src/'components/navbar/_brand.tsx','src="/favicon.svg"','src="/bracket/favicon.svg"')
patch(src/'main.tsx','defaultColorScheme="auto"','defaultColorScheme="dark"')
patch(root/'frontend/vite.config.ts','export default defineConfig({','export default defineConfig({\n  base: "/bracket/",')
patch(root/'frontend/i18n.ts',"fallbackLng: 'en',","fallbackLng: 'en',\n    backend: {loadPath: '/bracket/locales/{{lng}}/{{ns}}.json'},")
patch(src/'services/adapter.tsx',"Accept: 'application/json',","Accept: 'application/json',\n      'X-LAN-Request': '1',\n      'X-CSRF-Token': (window as any).__lispBracket?.csrf || '',")
patch(src/'main.tsx',"createRoot(document.getElementById('root')!).render(","""async function mountLispBracket() {
  const response = await fetch('/community-api/bracket-session', {cache: 'no-store'});
  if (!response.ok) { window.location.assign('/'); return; }
  const account = await response.json();
  (window as any).__lispBracket = account;
  localStorage.setItem('login', JSON.stringify({access_token: 'portal-session', user_id: account.user_id}));
  createRoot(document.getElementById('root')!).render(""")
p=src/'main.tsx';s=p.read_text(encoding='utf8')
if 'mountLispBracket();' not in s:p.write_text(s+'\n}\nmountLispBracket();\n',encoding='utf8')
(root/'frontend/.env.production').write_text('VITE_API_BASE_URL=/bracket-api/\n',encoding='utf8')
patch(src/'services/local_storage.tsx',"localStorage.removeItem('login');","localStorage.removeItem('login');\n  window.location.assign('/');")
print('Pinned Bracket frontend patched for local account SSO and /bracket/.')

patch(src/'components/navbar/_brand.tsx','          Bracket\n        </Text>', '          Bracket · <a href="/community-source/">Source</a>\n        </Text>')

patch(src/'main.tsx',"import { StrictMode } from 'react';", "import { Component, StrictMode } from 'react';")
patch(src/'main.tsx','async function mountLispBracket() {',"""class LispBracketBoundary extends Component<any, {error: Error | null}> {
  state = {error: null as Error | null};
  static getDerivedStateFromError(error: Error) { return {error}; }
  render() {
    if (this.state.error) return <div style={{padding: '2rem', color: 'white'}}><h1>Bracket view could not load</h1><p>{this.state.error.message}</p><a href="/tournaments/">Return to tournaments</a></div>;
    return this.props.children;
  }
}
async function mountLispBracket() {""")
patch(src/'main.tsx','  <StrictMode>', '  <LispBracketBoundary><StrictMode>')
patch(src/'main.tsx','  </StrictMode>,', '  </StrictMode></LispBracketBoundary>,')

patch(src/'pages/tournaments/[id]/stages/index.tsx','    return null;', '    return <Stack align="center" p="xl"><NoContent title="Tournament unavailable" description="This tournament was deleted or is not accessible." /><a href="/tournaments/">Return to tournaments</a></Stack>;')

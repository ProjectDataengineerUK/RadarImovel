import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Política de Privacidade — Mastavista",
  description: "Como a Mastavista coleta, usa e protege seus dados pessoais.",
};

export default function PrivacidadePage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white px-6 py-16">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-300 text-sm transition-colors mb-10">
          ← Voltar
        </Link>

        <div className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-blue-500 text-xl">⚖</span>
            <span className="font-bold text-lg">Mastavista</span>
          </div>
          <h1 className="text-3xl font-bold mb-2">Política de Privacidade</h1>
          <p className="text-gray-500 text-sm">Última atualização: junho de 2026</p>
        </div>

        <div className="prose prose-invert prose-sm max-w-none space-y-8 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">1. Quem somos</h2>
            <p>
              A Mastavista é uma plataforma de inteligência para monitoramento de leilões e vendas de imóveis
              de bancos públicos brasileiros. Operamos em conformidade com a Lei Geral de Proteção de Dados
              (LGPD — Lei nº 13.709/2018).
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">2. Dados que coletamos</h2>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li><span className="text-gray-300">Dados de cadastro:</span> nome, e-mail e foto de perfil (via Google OAuth ou cadastro por e-mail)</li>
              <li><span className="text-gray-300">Preferências de alerta:</span> estados, tipos de imóvel, faixa de preço e canal de notificação configurados por você</li>
              <li><span className="text-gray-300">Dados de uso:</span> páginas visitadas, filtros aplicados e imóveis visualizados (analytics anônimos)</li>
              <li><span className="text-gray-300">Dados de pagamento:</span> processados diretamente pelo Stripe — não armazenamos dados de cartão</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">3. Como usamos seus dados</h2>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li>Enviar alertas de imóveis de acordo com suas preferências (Telegram)</li>
              <li>Personalizar o painel e calcular scores relevantes para você</li>
              <li>Processar pagamentos de assinaturas</li>
              <li>Melhorar a plataforma com base em padrões de uso anônimos</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">4. Compartilhamento de dados</h2>
            <p className="text-gray-400">
              Não vendemos seus dados. Compartilhamos apenas com prestadores de serviço essenciais:
              Google (autenticação e infraestrutura), Stripe (pagamentos) e Telegram (envio de alertas).
              Todos operam com suas próprias políticas de privacidade.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">5. Seus direitos (LGPD)</h2>
            <p className="text-gray-400 mb-2">Você tem direito a:</p>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li>Confirmar a existência de tratamento dos seus dados</li>
              <li>Acessar, corrigir ou excluir seus dados</li>
              <li>Revogar consentimento a qualquer momento</li>
              <li>Portabilidade dos seus dados</li>
            </ul>
            <p className="text-gray-400 mt-3">
              Para exercer qualquer direito, envie um e-mail para{" "}
              <a href="mailto:privacidade@mastavista.com.br" className="text-blue-400 hover:text-blue-300">
                privacidade@mastavista.com.br
              </a>.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">6. Retenção de dados</h2>
            <p className="text-gray-400">
              Mantemos seus dados enquanto sua conta estiver ativa. Após exclusão da conta, os dados são
              removidos em até 30 dias, exceto quando obrigados por lei a mantê-los.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">7. Cookies</h2>
            <p className="text-gray-400">
              Usamos cookies estritamente necessários para autenticação e sessão. Não usamos cookies de
              rastreamento de terceiros para publicidade.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">8. Alterações nesta política</h2>
            <p className="text-gray-400">
              Podemos atualizar esta política. Notificaremos mudanças relevantes por e-mail ou aviso
              no painel com pelo menos 15 dias de antecedência.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">9. Contato</h2>
            <p className="text-gray-400">
              Dúvidas sobre privacidade:{" "}
              <a href="mailto:privacidade@mastavista.com.br" className="text-blue-400 hover:text-blue-300">
                privacidade@mastavista.com.br
              </a>
            </p>
          </section>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800 flex gap-6 text-sm text-gray-600">
          <Link href="/" className="hover:text-gray-300 transition-colors">Início</Link>
          <Link href="/termos" className="hover:text-gray-300 transition-colors">Termos de Uso</Link>
          <Link href="/planos" className="hover:text-gray-300 transition-colors">Planos</Link>
        </div>
      </div>
    </div>
  );
}

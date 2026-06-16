import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Termos de Uso — Mastavista",
  description: "Termos e condições de uso da plataforma Mastavista.",
};

export default function TermosPage() {
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
          <h1 className="text-3xl font-bold mb-2">Termos de Uso</h1>
          <p className="text-gray-500 text-sm">Última atualização: junho de 2026</p>
        </div>

        <div className="prose prose-invert prose-sm max-w-none space-y-8 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">1. Aceitação dos termos</h2>
            <p className="text-gray-400">
              Ao criar uma conta ou usar a Mastavista, você concorda com estes Termos de Uso. Se não concordar,
              não utilize a plataforma.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">2. Descrição do serviço</h2>
            <p className="text-gray-400">
              A Mastavista é uma plataforma de agregação e análise de informações sobre leilões e vendas de
              imóveis de bancos públicos e hastas judiciais. Os dados são coletados de fontes públicas e
              apresentados para fins informativos.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">3. Limitação de responsabilidade</h2>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-4">
              <p className="text-amber-300 text-sm font-medium">⚠️ Aviso importante</p>
              <p className="text-amber-200/70 text-sm mt-1">
                As informações da Mastavista são de caráter exclusivamente informativo e não constituem
                assessoria jurídica, financeira ou de investimento.
              </p>
            </div>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li>Não garantimos a exatidão, completude ou atualidade dos dados coletados de terceiros</li>
              <li>Não somos responsáveis por decisões de arrematação tomadas com base nas informações da plataforma</li>
              <li>Recomendamos sempre consultar o edital oficial e um advogado antes de participar de leilões</li>
              <li>Scores e análises de risco são estimativas algorítmicas, não laudos periciais</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">4. Uso permitido</h2>
            <p className="text-gray-400 mb-2">Você pode usar a Mastavista para:</p>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li>Monitorar leilões de imóveis para uso pessoal ou profissional</li>
              <li>Configurar alertas e receber notificações</li>
              <li>Analisar oportunidades e calcular ROI estimado</li>
            </ul>
            <p className="text-gray-400 mt-3 mb-2">É proibido:</p>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li>Raspar ou exportar dados em massa por meios automatizados</li>
              <li>Revender ou redistribuir os dados da plataforma</li>
              <li>Usar a plataforma para fins ilegais</li>
              <li>Compartilhar credenciais de acesso com terceiros</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">5. Assinaturas e pagamentos</h2>
            <ul className="list-disc list-inside space-y-1.5 text-gray-400">
              <li>Os planos pagos são cobrados via Stripe, antecipadamente (mensal ou anual)</li>
              <li>Você pode cancelar a qualquer momento; o acesso Premium dura até o fim do período pago</li>
              <li>Não há reembolso proporcional para cancelamentos no meio do período, exceto em casos previstos pelo Código de Defesa do Consumidor</li>
              <li>O plano gratuito permanece disponível indefinidamente sem cobrança</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">6. Propriedade intelectual</h2>
            <p className="text-gray-400">
              O código, design, marca e algoritmos da Mastavista são de propriedade exclusiva da plataforma.
              Os dados coletados de fontes públicas são de domínio público e não pertencem à Mastavista.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">7. Disponibilidade</h2>
            <p className="text-gray-400">
              Nos esforçamos para manter a plataforma disponível 24/7, mas não garantimos disponibilidade
              ininterrupta. Manutenções programadas serão comunicadas com antecedência.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">8. Alterações nos termos</h2>
            <p className="text-gray-400">
              Podemos alterar estes termos mediante aviso com pelo menos 15 dias de antecedência por e-mail.
              O uso continuado da plataforma após a vigência das alterações implica aceitação.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">9. Foro e lei aplicável</h2>
            <p className="text-gray-400">
              Estes termos são regidos pelas leis brasileiras. Fica eleito o foro da comarca de São Paulo/SP
              para dirimir eventuais conflitos.
            </p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-3">10. Contato</h2>
            <p className="text-gray-400">
              Dúvidas sobre estes termos:{" "}
              <a href="mailto:contato@mastavista.com.br" className="text-blue-400 hover:text-blue-300">
                contato@mastavista.com.br
              </a>
            </p>
          </section>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800 flex gap-6 text-sm text-gray-600">
          <Link href="/" className="hover:text-gray-300 transition-colors">Início</Link>
          <Link href="/privacidade" className="hover:text-gray-300 transition-colors">Privacidade</Link>
          <Link href="/planos" className="hover:text-gray-300 transition-colors">Planos</Link>
        </div>
      </div>
    </div>
  );
}

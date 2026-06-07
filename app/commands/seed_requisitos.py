import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app.models import (
    AditivoAlimentar,
    Alimento,
    AlimentoAditivo,
    CalculoETA,
    ConsistenciaFisica,
    ItemRefeicao,
    LaudoMetabolico,
    MarcadorDisbiose,
    RelatorioExportavel,
    ScoreRiscoCardio,
    SimulacaoRefeicao,
    SugestaoTroca,
)

class Command(BaseCommand):
    help = "Cria registros base para demonstrar o fluxo do projeto."


    def handle(self, *args, **options):
        self._criar_admin()
        consistencias = self._criar_consistencias()
        aditivos = self._criar_aditivos()
        alimentos = self._criar_alimentos(consistencias)
        self._criar_associacoes(alimentos, aditivos)
        self._criar_trocas(alimentos)
        simulacoes = self._criar_simulacoes(alimentos)
        self._criar_resultados(simulacoes)
        self._mostrar_resumo()

    def _criar_admin(self):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(username="admin", password="1234")

    def _criar_consistencias(self):
        dados = [
            ("Líquida", "Baixo", "Textura com baixo esforço mastigatório e ingestão mais rápida."),
            ("Cremosa", "Moderado", "Textura pastosa, comum em vitaminas e cremes."),
            ("Crocante", "Alto", "Exige mastigação mais intensa e tende a desacelerar a ingestão."),
            ("Macia", "Moderado", "Textura fácil de mastigar, mas ainda sólida."),
            ("Fibrosa", "Alto", "Maior exigência mecânica pela presença de fibras."),
        ]
        return {
            tipo: ConsistenciaFisica.objects.update_or_create(
                tipo_textura=tipo,
                defaults={"esforco_mastigatorio": esforco, "observacao": observacao},
            )[0]
            for tipo, esforco, observacao in dados
        }

    def _criar_aditivos(self):
        dados = [
            ("Tartrazina", "Corante", AditivoAlimentar.RISCO_MEDIO, "Pode exigir atenção em indivíduos sensíveis a corantes."),
            ("Fosfato de Sódio", "Estabilizador", AditivoAlimentar.RISCO_ALTO, "Componente que pede atenção na leitura do rótulo."),
            ("Mono e Diglicerídeos", "Emulsionante", AditivoAlimentar.RISCO_ALTO, "Componente usado para observar melhor a composição da refeição."),
            ("Nitrito de Sódio", "Conservante", AditivoAlimentar.RISCO_MEDIO, "Conservante comum em carnes processadas."),
            ("Gordura Vegetal Hidrogenada", "Gordura trans", AditivoAlimentar.RISCO_ALTO, "Marcador de potencial aterogênico elevado."),
        ]
        return {
            nome: AditivoAlimentar.objects.update_or_create(
                nome_quimico=nome,
                defaults={
                    "funcao_tecnologica": funcao,
                    "grau_risco": risco,
                    "impacto_fisiologico": impacto,
                },
            )[0]
            for nome, funcao, risco, impacto in dados
        }

    def _criar_alimentos(self, consistencias):
        dados = [
            ("Arroz integral", Alimento.NOVA_1, 124, 100, "Fibrosa", "Base simples para refeições do dia a dia."),
            ("Suco de laranja natural", Alimento.NOVA_1, 45, 100, "Líquida", "Alternativa natural para bebidas adoçadas."),
            ("Maçã com casca", Alimento.NOVA_1, 52, 100, "Crocante", "Fruta com fibra e alto esforço de mastigação."),
            ("Refrigerante cola", Alimento.NOVA_4, 42, 100, "Líquida", "Opção muito industrializada e líquida, com baixo esforço de mastigação."),
            ("Nuggets industrializados", Alimento.NOVA_4, 290, 100, "Macia", "Opção muito industrializada, com componentes e gordura adicionada."),
        ]
        return {
            nome: Alimento.objects.update_or_create(
                nome=nome,
                defaults={
                    "categoria_nova": categoria,
                    "energia_kcal": energia,
                    "porcao_g": porcao,
                    "consistencia": consistencias[textura],
                    "observacao_metabolica": observacao,
                },
            )[0]
            for nome, categoria, energia, porcao, textura, observacao in dados
        }

    def _criar_associacoes(self, alimentos, aditivos):
        dados = [
            ("Refrigerante cola", "Tartrazina", "Corante usado como exemplo de componente do rótulo."),
            ("Refrigerante cola", "Fosfato de Sódio", "Estabilizador que pede atenção na leitura do rótulo."),
            ("Nuggets industrializados", "Mono e Diglicerídeos", "Emulsionante usado para observação da composição."),
            ("Nuggets industrializados", "Nitrito de Sódio", "Conservante comum em produtos cárneos processados."),
            ("Nuggets industrializados", "Gordura Vegetal Hidrogenada", "Marcador de gordura trans para o score cardíaco."),
        ]
        for alimento, aditivo, observacao in dados:
            AlimentoAditivo.objects.update_or_create(
                alimento=alimentos[alimento],
                aditivo=aditivos[aditivo],
                defaults={"observacao": observacao},
            )

    def _criar_trocas(self, alimentos):
        dados = [
            ("Refrigerante cola", "Suco de laranja natural", "Troca uma bebida muito industrializada por uma opção mais simples."),
            ("Refrigerante cola", "Maçã com casca", "Aumenta mastigação e fibra no lugar de bebida líquida adoçada."),
            ("Refrigerante cola", "Arroz integral", "Exemplo didático para reduzir componentes de atenção em um prato completo."),
            ("Nuggets industrializados", "Arroz integral", "Troca reduz gordura adicionada e componentes de atenção."),
            ("Nuggets industrializados", "Maçã com casca", "Sugestão educativa para trocar por uma opção mais simples."),
        ]
        for ruim, substituto, justificativa in dados:
            SugestaoTroca.objects.update_or_create(
                alimento_ultraprocessado=alimentos[ruim],
                alimento_substituto_innatura=alimentos[substituto],
                defaults={"justificativa": justificativa},
            )

    def _criar_simulacoes(self, alimentos):
        dados = [
            ("11111111-1111-4111-8111-111111111111", "Arroz integral", 150),
            ("22222222-2222-4222-8222-222222222222", "Suco de laranja natural", 250),
            ("33333333-3333-4333-8333-333333333333", "Maçã com casca", 130),
            ("44444444-4444-4444-8444-444444444444", "Refrigerante cola", 350),
            ("55555555-5555-4555-8555-555555555555", "Nuggets industrializados", 180),
        ]
        simulacoes = []
        for identificador, alimento, quantidade in dados:
            simulacao, _ = SimulacaoRefeicao.objects.get_or_create(
                identificador_sessao=uuid.UUID(identificador)
            )
            ItemRefeicao.objects.get_or_create(
                simulacao_refeicao=simulacao,
                alimento=alimentos[alimento],
                quantidade_g=quantidade,
            )
            simulacao.calcular_peso_total()
            simulacoes.append(simulacao)
        return simulacoes

    def _criar_resultados(self, simulacoes):
        for simulacao in simulacoes:
            eta, _ = CalculoETA.objects.get_or_create(simulacao_refeicao=simulacao)
            cardio, _ = ScoreRiscoCardio.objects.get_or_create(simulacao_refeicao=simulacao)
            disbiose, _ = MarcadorDisbiose.objects.get_or_create(simulacao_refeicao=simulacao)
            laudo, _ = LaudoMetabolico.objects.get_or_create(simulacao_refeicao=simulacao)
            eta.calcular_depreciacao_eta()
            cardio.calcular_score_cumulativo()
            disbiose.mapear_perturbacao_microbiota()
            laudo.compilar_laudo_comparativo()
            RelatorioExportavel.objects.get_or_create(laudo_metabolico=laudo, formato_saida="HTML")

    def _mostrar_resumo(self):
        contagens = {
            "RF01 Alimentos": Alimento.objects.count(),
            "RF02 Componentes": AditivoAlimentar.objects.count(),
            "RF03 Associações": AlimentoAditivo.objects.count(),
            "RF04 Consistências": ConsistenciaFisica.objects.count(),
            "RF05 Simulações": SimulacaoRefeicao.objects.count(),
            "RF06 Itens": ItemRefeicao.objects.count(),
            "RF07 Gastos estimados": CalculoETA.objects.count(),
            "RF08 Atenções ao coração": ScoreRiscoCardio.objects.count(),
            "RF09 Alertas intestinais": MarcadorDisbiose.objects.count(),
            "RF10 Sugestões de troca": SugestaoTroca.objects.count(),
            "RF11 Resumos": LaudoMetabolico.objects.count(),
            "RF15 Relatórios": RelatorioExportavel.objects.count(),
        }
        for nome, total in contagens.items():
            self.stdout.write(f"{nome}: {total}")
        self.stdout.write(self.style.SUCCESS("Carga inicial concluída."))

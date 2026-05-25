import uuid
from django.db import models


class ConsistenciaFisica(models.Model):
    """
    RF04: Avaliar a consistência física e taxa de mastigação.
    """
    tipo_textura = models.CharField(max_length=100, help_text="Ex: Líquida, Pastosa, Sólida")
    esforco_mastigatorio = models.CharField(max_length=100, help_text="Ex: Baixo, Moderado, Alto")

    def __str__(self):
        return f"{self.tipo_textura} (Mastigação: {self.esforco_mastigatorio})"

    def avaliar_taxa_mastigacao(self):
        """
        Regra: Textura líquida indica baixo esforço e ingestão acelerada (SBPC).
        """
        if self.tipo_textura.lower() == 'líquida' or self.tipo_textura.lower() == 'liquida':
            return "Alerta: Textura líquida indica baixo esforço mecânico e ingestão acelerada."
        return "Taxa de mastigação dentro dos parâmetros normais para a consistência."


class AditivoAlimentare(models.Model):
    """
    RF02: Mapear Aditivos Químicos industriais.
    """
    nome_quimico = models.CharField(max_length=150, help_text="Ex: Tartrazina, Fosfato de Sódio")
    funcao_tecnologica = models.CharField(max_length=100, help_text="Ex: Corante, Estabilizador, Emulsionante")
    grau_risco = models.CharField(max_length=50, help_text="Ex: Baixo, Médio, Alto")

    def __str__(self):
        return f"{self.nome_quimico} ({self.funcao_tecnologica})"


class Alimento(models.Model):
    """
    RF01: Analisar a Classificação nova do Alimento.
    """
    nome = models.CharField(max_length=150)
    categoria_nova = models.CharField(max_length=50, help_text="Ex: NOVA 1 (In Natura), NOVA 4 (Ultraprocessado)")
    energia_kcal = models.FloatField(help_text="Valor energético por porção")
    porcao_g = models.FloatField(help_text="Peso da porção de referência em gramas")
    consistencia = models.ForeignKey(ConsistenciaFisica, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.categoria_nova})"


class AlimentoAditivo(models.Model):
    """
    RF03: Associar múltiplos aditivos aos alimentos (Tabela de Associação).
    """
    alimento = models.ForeignKey(Alimento, on_delete=models.CASCADE)
    aditivo = models.ForeignKey(AditivoAlimentare, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('alimento', 'aditivo')

    def __str__(self):
        return f"{self.alimento.nome} -> {self.aditivo.nome_quimico}"


class SimulacaoRefeicoe(models.Model):
    """
    RF05: Instanciar cenário de simulação (Prato Virtual).
    """
    identificador_sessao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    data_simulacao = models.DateTimeField(auto_now_add=True)
    peso_total_g = models.FloatField(default=0.0)

    def __str__(self):
        return f"Simulação {self.identificador_sessao} - {self.data_simulacao.strftime('%d/%m/%Y')}"

    def calcular_peso_total(self):
        """
        Calcula o peso total somando as quantidades de todos os itens associados.
        """
        itens = self.itens.all()
        self.peso_total_g = sum(item.quantidade_g for item in itens)
        self.save()
        return self.peso_total_g


class ItemRefeicoe(models.Model):
    """
    RF06: Computar os alimentos integrados na simulação ativa.
    """
    simulacao_refeicao = models.ForeignKey(SimulacaoRefeicoe, on_delete=models.CASCADE, related_name="itens")
    alimento = models.ForeignKey(Alimento, on_delete=models.CASCADE)
    quantidade_g = models.FloatField(help_text="Quantidade inserida no prato pelo usuário")

    def __str__(self):
        return f"{self.quantidade_g}g de {self.alimento.nome}"


class Calculo(models.Model):
    """
    RF07: Calcular o Efeito Térmico do Alimento (ETA).
    """
    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicoe, on_delete=models.CASCADE, related_name="calculo_eta")
    eta_basal_kcal = models.FloatField(default=0.0)
    etapa_final_kcal = models.FloatField(default=0.0)
    percentual_queda = models.FloatField(default=0.0)

    def calcular_depreciacao_eta(self):
        """
        Regra: Queda de 30% na eficiência energética digestiva por uso de ultraprocessados (NOVA 4).
        """
        itens = self.simulacao_refeicao.itens.all()
        contem_ultraprocessado = any(item.alimento.categoria_nova.upper() == 'NOVA 4' for item in itens)
        
        # Cálculo básico hipotético do ETA basal (ex: 10% da energia total dos alimentos)
        energia_total = sum((item.alimento.energia_kcal * item.quantidade_g / item.alimento.porcao_g) for item in itens)
        self.eta_basal_kcal = energia_total * 0.10

        if contem_ultraprocessado:
            self.percentual_queda = 30.0
            self.etapa_final_kcal = self.eta_basal_kcal * 0.70 # Retira os 30%
        else:
            self.percentual_queda = 0.0
            self.etapa_final_kcal = self.eta_basal_kcal
        
        self.save()


class RiscoCardiaco(models.Model):
    """
    RF08: Calcular o Score de Risco Cardiovascular cumulativo.
    """
    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicoe, on_delete=models.CASCADE, related_name="score_cardio")
    pontuacao_risco = models.IntegerField(default=0)
    potencial_aterogenico = models.CharField(max_length=100, default="Normal")

    def calcular_score_cumulativo(self):
        """
        Regra: Risco elevado por consumo associado de gorduras trans e fosfatos (TCC).
        """
        itens = self.simulacao_refeicao.itens.all()
        possui_fosfato = False
        possui_trans = False

        for item in itens:
            # Varre os aditivos do alimento do item
            aditivos_vinculados = AlimentoAditivo.objects.filter(alimento=item.alimento)
            for vinculo in aditivos_vinculados:
                nome_aditivo = vinculo.aditivo.nome_quimico.lower()
                if 'fosfato' in nome_aditivo:
                    possui_fosfato = True
            
            # Validação simples de gordura trans pelo nome do item ou marcador (ajustável)
            if 'gordura trans' in item.alimento.nome.lower() or item.alimento.categoria_nova.upper() == 'NOVA 4':
                possui_trans = True

        if possui_fosfato and possui_trans:
            self.pontuacao_risco = 100
            self.potencial_aterogenico = "Risco Coronário Elevado"
        else:
            self.pontuacao_risco = 10
            self.potencial_aterogenico = "Risco Controlado"
        
        self.save()


class MarcadorDisbiose(models.Model):
    """
    RF09: Mapear Marcadores de Perturbação da Microbiota.
    """
    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicoe, on_delete=models.CASCADE, related_name="marcador_disbiose")
    risco_permeabilidade = models.CharField(max_length=50, default="Baixo")
    descricao_alerta = models.TextField(blank=True, default="")

    def mapear_perturbacao_microbiota(self):
        """
        Regra: Sinalização de risco devido à presença de emulsionantes na dieta.
        """
        itens = self.simulacao_refeicao.itens.all()
        possui_emulsionante = False

        for item in itens:
            aditivos_vinculados = AlimentoAditivo.objects.filter(alimento=item.alimento)
            for vinculo in aditivos_vinculados:
                if vinculo.aditivo.funcao_tecnologica.lower() == 'emulsionante':
                    possui_emulsionante = True
                    break

        if possui_emulsionante:
            self.risco_permeabilidade = "Alto"
            self.descricao_alerta = "Sinalização de risco de permeabilidade intestinal devido à presença cumulativa de emulsionantes na dieta."
        else:
            self.risco_permeabilidade = "Baixo"
            self.descricao_alerta = "Microbiota preservada com base nos aditivos analisados."
        
        self.save()


class SugestaoTroca(models.Model):
    """
    RF11: Executar algoritmo de substituição inteligente.
    """
    alimento_ultraprocessado = models.ForeignKey(Alimento, on_delete=models.CASCADE, related_name="trocas_como_ruim")
    alimento_substituto_innatura = models.ForeignKey(Alimento, on_delete=models.CASCADE, related_name="trocas_como_substituto")

    def __str__(self):
        return f"Trocar {self.alimento_ultraprocessado.nome} por {self.alimento_substituto_innatura.nome}"

    @classmethod
    def executar_substituicao_inteligente(cls, alimento):
        """
        Busca uma sugestão pré-mapeada para o alimento nocivo enviado.
        Exemplo do documento: Sugerir a troca de 'Suco em pó' por 'Suco de laranja natural'.
        """
        sugestao = cls.objects.filter(alimento_ultraprocessado=alimento).first()
        if sugestao:
            return f"Sugestão de substituição inteligente: Substitua '{alimento.nome}' por '{sugestao.alimento_substituto_innatura.nome}' para mitigar danos metabólicos."
        return "Nenhuma sugestão de substituição direta mapeada para este alimento."


class LaudoMetabolico(models.Model):
    """
    RF10: Compilar laudo clínico-nutricional comparativo.
    """
    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicoe, on_delete=models.CASCADE, related_name="laudo")
    texto_sintese = models.TextField()
    classe_alerta_css = models.CharField(max_length=50, help_text="Injeta a classe CSS correspondente ao nível de risco cromático")

    def __str__(self):
        return f"Laudo Metabólico - {self.simulacao_refeicao.identificador_sessao}"

    def compilar_laudo_comparativo(self):
        """
        Gera a síntese final unificando o ETA, Score Cardio e Disbiose.
        Regra: Texto a contrastar o ritmo de ingestão e alteração do perfil lipídico. Injeta realce cromático para risco coronário.
        """
        # Dispara os cálculos das tabelas dependentes primeiro
        self.simulacao_refeicao.calculo_eta.calcular_depreciacao_eta()
        self.simulacao_refeicao.score_cardio.calcular_score_cumulativo()
        self.simulacao_refeicao.marcador_disbiose.mapear_perturbacao_microbiota()

        eta = self.simulacao_refeicao.calculo_eta
        cardio = self.simulacao_refeicao.score_cardio
        disbiose = self.simulacao_refeicao.marcador_disbiose

        # Define a classe de estilo CSS baseada no risco cardiovascular do laudo
        if cardio.potencial_aterogenico == "Risco Coronário Elevado":
            self.classe_alerta_css = "alert-danger-cronico" # Vermelho
        elif disbiose.risco_permeabilidade == "Alto":
            self.classe_alerta_css = "alert-warning-intestinal" # Amarelo/Laranja
        else:
            self.classe_alerta_css = "alert-success-metabolico" # Verde

        # Constrói o texto descritivo clínico exigido
        self.texto_sintese = (
            f"Laudo Clínico: A análise metabólica identificou um Efeito Térmico do Alimento (ETA) final de "
            f"{eta.etapa_final_kcal:.2f} kcal (Queda de {eta.percentual_queda}%). O perfil lipídico apresenta "
            f"potencial de desequilíbrio categorizado como '{cardio.potencial_aterogenico}'. "
            f"O ritmo de ingestão acelerada em conjunto com os marcadores intestinais indica: {disbiose.descricao_alerta}"
        )
        self.save()


class Relatorio(models.Model):
    """
    RF15: Exportar diagnóstico metabólico estruturado.
    """
    laudo_metabolico = models.ForeignKey(LaudoMetabolico, on_delete=models.CASCADE, related_name="exportacoes")
    formato_saida = models.CharField(max_length=10, default="HTML")

    def gerar_documento_html(self):
        """
        Retorna a estrutura ou string HTML limpa e otimizada para impressão.
        """
        laudo = self.laudo_metabolico
        html_template = f"""
        <div class="{laudo.classe_alerta_css}">
            <h1>Laudo Metabólico Estruturado</h1>
            <p><strong>Sessão:</strong> {laudo.simulacao_refeicao.identificador_sessao}</p>
            <p><strong>Diagnóstico Clínico:</strong> {laudo.texto_sintese}</p>
            <p><strong>Peso Total Calculado do Prato:</strong> {laudo.simulacao_refeicao.peso_total_g}g</p>
        </div>
        """
        return html_template
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class ConsistenciaFisica(models.Model):
    """RF04 - Avalia textura, esforço mastigatório e ritmo provável de ingestão."""

    tipo_textura = models.CharField(max_length=100, help_text="Ex.: Líquida, Pastosa, Sólida")
    esforco_mastigatorio = models.CharField(max_length=100, help_text="Ex.: Baixo, Moderado, Alto")
    observacao = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Consistência física"
        verbose_name_plural = "Consistências físicas"
        ordering = ["tipo_textura"]

    def __str__(self) -> str:
        return f"{self.tipo_textura} - esforço {self.esforco_mastigatorio}"

    def avaliar_taxa_mastigacao(self) -> str:
        textura = self.tipo_textura.lower()
        esforco = self.esforco_mastigatorio.lower()
        if "líquid" in textura or "liquid" in textura or "baixo" in esforco:
            return "Baixo esforço mastigatório: pode favorecer ingestão mais rápida e menor percepção de saciedade."
        if "alto" in esforco:
            return "Alto esforço mastigatório: tende a exigir maior tempo de mastigação e ingestão mais lenta."
        return "Esforço mastigatório intermediário, com impacto moderado no ritmo de ingestão."


class AditivoAlimentar(models.Model):
    """RF02 e RF13 - Cadastro e painel toxicológico de aditivos."""

    RISCO_BAIXO = "Baixo"
    RISCO_MEDIO = "Médio"
    RISCO_ALTO = "Alto"
    RISCO_CHOICES = [
        (RISCO_BAIXO, "Baixo"),
        (RISCO_MEDIO, "Médio"),
        (RISCO_ALTO, "Alto"),
    ]

    nome_quimico = models.CharField(max_length=150, unique=True, help_text="Ex.: Tartrazina, Fosfato de Sódio")
    funcao_tecnologica = models.CharField(max_length=120, help_text="Ex.: Corante, Estabilizador, Emulsionante")
    grau_risco = models.CharField(max_length=20, choices=RISCO_CHOICES, default=RISCO_BAIXO)
    impacto_fisiologico = models.TextField(
        blank=True,
        default="Impacto fisiológico não descrito na base. Complete este campo com a evidência usada no projeto.",
    )

    class Meta:
        verbose_name = "Aditivo alimentar"
        verbose_name_plural = "Aditivos alimentares"
        ordering = ["nome_quimico"]

    def __str__(self) -> str:
        return f"{self.nome_quimico} ({self.funcao_tecnologica})"

    @property
    def classe_risco_css(self) -> str:
        return {
            self.RISCO_ALTO: "danger",
            self.RISCO_MEDIO: "warning",
            self.RISCO_BAIXO: "success",
        }.get(self.grau_risco, "secondary")


class Alimento(models.Model):
    """RF01, RF12 - Cadastro, classificação NOVA e catálogo público de alimentos."""

    NOVA_1 = "NOVA 1"
    NOVA_2 = "NOVA 2"
    NOVA_3 = "NOVA 3"
    NOVA_4 = "NOVA 4"
    NOVA_CHOICES = [
        (NOVA_1, "NOVA 1 - In natura ou minimamente processado"),
        (NOVA_2, "NOVA 2 - Ingrediente culinário processado"),
        (NOVA_3, "NOVA 3 - Processado"),
        (NOVA_4, "NOVA 4 - Ultraprocessado"),
    ]

    nome = models.CharField(max_length=150, unique=True)
    categoria_nova = models.CharField(max_length=20, choices=NOVA_CHOICES, db_index=True)
    energia_kcal = models.FloatField(validators=[MinValueValidator(0)], help_text="Valor energético por porção")
    porcao_g = models.FloatField(validators=[MinValueValidator(1)], help_text="Peso da porção de referência em gramas")
    consistencia = models.ForeignKey(ConsistenciaFisica, on_delete=models.SET_NULL, null=True, blank=True)
    observacao_metabolica = models.TextField(blank=True, default="")
    aditivos = models.ManyToManyField(AditivoAlimentar, through="AlimentoAditivo", blank=True, related_name="alimentos")

    class Meta:
        verbose_name = "Alimento"
        verbose_name_plural = "Alimentos"
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.categoria_nova})"

    @property
    def categoria_numero(self) -> int:
        try:
            return int(self.categoria_nova.split()[1])
        except (IndexError, ValueError):
            return 0

    @property
    def categoria_css(self) -> str:
        return {
            self.NOVA_1: "success",
            self.NOVA_2: "primary",
            self.NOVA_3: "warning",
            self.NOVA_4: "danger",
        }.get(self.categoria_nova, "secondary")

    def indice_integridade(self) -> int:
        """RF complementar - Índice de Integridade por regras lógicas.

        Regra pedagógica: parte de 100 e desconta pontos por grau de processamento,
        presença de aditivos críticos e consistência de baixo esforço mastigatório.
        """
        pontuacao = 100
        pontuacao -= {self.NOVA_1: 0, self.NOVA_2: 15, self.NOVA_3: 35, self.NOVA_4: 60}.get(self.categoria_nova, 25)

        for aditivo in self.aditivos.all():
            if aditivo.grau_risco == AditivoAlimentar.RISCO_ALTO:
                pontuacao -= 15
            elif aditivo.grau_risco == AditivoAlimentar.RISCO_MEDIO:
                pontuacao -= 8
            else:
                pontuacao -= 3

        if self.consistencia and "baixo" in self.consistencia.esforco_mastigatorio.lower():
            pontuacao -= 8

        return max(0, min(100, pontuacao))

    def classe_integridade_css(self) -> str:
        score = self.indice_integridade()
        if score >= 75:
            return "success"
        if score >= 45:
            return "warning"
        return "danger"

    def resumo_aditivos(self) -> str:
        nomes = list(self.aditivos.values_list("nome_quimico", flat=True))
        return ", ".join(nomes) if nomes else "Sem aditivos críticos cadastrados"


class AlimentoAditivo(models.Model):
    """RF03 - Associação de múltiplos aditivos aos alimentos."""

    alimento = models.ForeignKey(Alimento, on_delete=models.CASCADE)
    aditivo = models.ForeignKey(AditivoAlimentar, on_delete=models.CASCADE)
    observacao = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Associação alimento-aditivo"
        verbose_name_plural = "Associações alimento-aditivo"
        unique_together = ("alimento", "aditivo")
        ordering = ["alimento__nome", "aditivo__nome_quimico"]

    def __str__(self) -> str:
        return f"{self.alimento.nome} → {self.aditivo.nome_quimico}"


class SimulacaoRefeicao(models.Model):
    """RF05 - Prato virtual."""

    identificador_sessao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    data_simulacao = models.DateTimeField(default=timezone.now)
    peso_total_g = models.FloatField(default=0.0, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Simulação de refeição"
        verbose_name_plural = "Simulações de refeição"
        ordering = ["-data_simulacao"]

    def __str__(self) -> str:
        return f"Simulação {self.identificador_sessao}"

    def calcular_peso_total(self) -> float:
        self.peso_total_g = sum(item.quantidade_g for item in self.itens.select_related("alimento"))
        self.save(update_fields=["peso_total_g"])
        return self.peso_total_g

    def energia_total(self) -> float:
        return sum(item.energia_calculada() for item in self.itens.select_related("alimento"))

    def possui_itens(self) -> bool:
        return self.itens.exists()


class ItemRefeicao(models.Model):
    """RF06 - Alimentos integrados à simulação ativa."""

    simulacao_refeicao = models.ForeignKey(SimulacaoRefeicao, on_delete=models.CASCADE, related_name="itens")
    alimento = models.ForeignKey(Alimento, on_delete=models.CASCADE)
    quantidade_g = models.FloatField(validators=[MinValueValidator(1)], help_text="Quantidade em gramas")

    class Meta:
        verbose_name = "Item da refeição"
        verbose_name_plural = "Itens da refeição"

    def __str__(self) -> str:
        return f"{self.quantidade_g:g}g de {self.alimento.nome}"

    def energia_calculada(self) -> float:
        return (self.alimento.energia_kcal * self.quantidade_g) / self.alimento.porcao_g


class CalculoETA(models.Model):
    """RF07 - Efeito Térmico do Alimento estimado."""

    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicao, on_delete=models.CASCADE, related_name="calculo_eta")
    eta_basal_kcal = models.FloatField(default=0.0)
    etapa_final_kcal = models.FloatField(default=0.0)
    percentual_queda = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        verbose_name = "Cálculo de ETA"
        verbose_name_plural = "Cálculos de ETA"

    def calcular_depreciacao_eta(self) -> "CalculoETA":
        energia_total = self.simulacao_refeicao.energia_total()
        self.eta_basal_kcal = energia_total * 0.10
        proporcao_ultra = 0.0
        peso_total = self.simulacao_refeicao.calcular_peso_total()
        if peso_total:
            peso_ultra = sum(
                item.quantidade_g
                for item in self.simulacao_refeicao.itens.select_related("alimento")
                if item.alimento.categoria_nova == Alimento.NOVA_4
            )
            proporcao_ultra = peso_ultra / peso_total
        self.percentual_queda = round(30 * proporcao_ultra, 2)
        self.etapa_final_kcal = round(self.eta_basal_kcal * (1 - self.percentual_queda / 100), 2)
        self.save()
        return self


class ScoreRiscoCardio(models.Model):
    """RF08 - Score cumulativo de risco cardiovascular estimativo."""

    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicao, on_delete=models.CASCADE, related_name="score_cardio")
    pontuacao_risco = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    potencial_aterogenico = models.CharField(max_length=120, default="Não calculado")

    class Meta:
        verbose_name = "Score de risco cardiovascular"
        verbose_name_plural = "Scores de risco cardiovascular"

    def calcular_score_cumulativo(self) -> "ScoreRiscoCardio":
        score = 0
        possui_fosfato = False
        possui_gordura_hidrogenada = False

        for item in self.simulacao_refeicao.itens.select_related("alimento").prefetch_related("alimento__aditivos"):
            if item.alimento.categoria_nova == Alimento.NOVA_4:
                score += 25
            elif item.alimento.categoria_nova == Alimento.NOVA_3:
                score += 12

            for aditivo in item.alimento.aditivos.all():
                nome = aditivo.nome_quimico.lower()
                if aditivo.grau_risco == AditivoAlimentar.RISCO_ALTO:
                    score += 20
                elif aditivo.grau_risco == AditivoAlimentar.RISCO_MEDIO:
                    score += 10
                if "fosfato" in nome:
                    possui_fosfato = True
                if "hidrogen" in nome or "trans" in nome:
                    possui_gordura_hidrogenada = True

        if possui_fosfato and possui_gordura_hidrogenada:
            score += 20

        self.pontuacao_risco = min(100, score)
        if self.pontuacao_risco >= 70:
            self.potencial_aterogenico = "Elevado"
        elif self.pontuacao_risco >= 35:
            self.potencial_aterogenico = "Moderado"
        else:
            self.potencial_aterogenico = "Baixo"
        self.save()
        return self

    @property
    def classe_css(self) -> str:
        if self.pontuacao_risco >= 70:
            return "danger"
        if self.pontuacao_risco >= 35:
            return "warning"
        return "success"


class MarcadorDisbiose(models.Model):
    """RF09 - Marcadores de perturbação da microbiota."""

    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicao, on_delete=models.CASCADE, related_name="marcador_disbiose")
    risco_permeabilidade = models.CharField(max_length=50, default="Baixo")
    descricao_alerta = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Marcador de disbiose"
        verbose_name_plural = "Marcadores de disbiose"

    def mapear_perturbacao_microbiota(self) -> "MarcadorDisbiose":
        encontrou_emulsionante = False
        encontrou_corante = False
        for item in self.simulacao_refeicao.itens.select_related("alimento").prefetch_related("alimento__aditivos"):
            for aditivo in item.alimento.aditivos.all():
                funcao = aditivo.funcao_tecnologica.lower()
                if "emulsionante" in funcao:
                    encontrou_emulsionante = True
                if "corante" in funcao:
                    encontrou_corante = True

        if encontrou_emulsionante:
            self.risco_permeabilidade = "Alto"
            self.descricao_alerta = "Presença de emulsionantes: sinalizar risco aumentado de perturbação da microbiota."
        elif encontrou_corante:
            self.risco_permeabilidade = "Moderado"
            self.descricao_alerta = "Presença de corantes/aditivos: recomenda-se atenção à composição do prato."
        else:
            self.risco_permeabilidade = "Baixo"
            self.descricao_alerta = "Sem marcadores críticos de disbiose cadastrados para os itens selecionados."
        self.save()
        return self

    @property
    def classe_css(self) -> str:
        return {"Alto": "danger", "Moderado": "warning", "Baixo": "success"}.get(self.risco_permeabilidade, "secondary")


class SugestaoTroca(models.Model):
    """RF10 - Substituição inteligente."""

    alimento_ultraprocessado = models.ForeignKey(Alimento, on_delete=models.CASCADE, related_name="trocas_como_ruim")
    alimento_substituto_innatura = models.ForeignKey(Alimento, on_delete=models.CASCADE, related_name="trocas_como_substituto")
    justificativa = models.TextField(blank=True, default="Troca sugerida para reduzir processamento e aditivos críticos.")

    class Meta:
        verbose_name = "Sugestão de troca"
        verbose_name_plural = "Sugestões de troca"
        unique_together = ("alimento_ultraprocessado", "alimento_substituto_innatura")

    def __str__(self) -> str:
        return f"Trocar {self.alimento_ultraprocessado.nome} por {self.alimento_substituto_innatura.nome}"

    @classmethod
    def executar_substituicao_inteligente(cls, alimento: Alimento) -> str:
        sugestao = cls.objects.filter(alimento_ultraprocessado=alimento).select_related("alimento_substituto_innatura").first()
        if sugestao:
            return f"Troque {alimento.nome} por {sugestao.alimento_substituto_innatura.nome}. {sugestao.justificativa}"
        if alimento.categoria_nova == Alimento.NOVA_4:
            return "Ultraprocessado identificado. Cadastre uma alternativa in natura ou minimamente processada para completar a sugestão."
        return "Este alimento não exige substituição prioritária pela regra atual."


class LaudoMetabolico(models.Model):
    """RF11 - Laudo comparativo/educativo da simulação."""

    simulacao_refeicao = models.OneToOneField(SimulacaoRefeicao, on_delete=models.CASCADE, related_name="laudo")
    texto_sintese = models.TextField(blank=True, default="")
    classe_alerta_css = models.CharField(max_length=50, default="alert-success")

    class Meta:
        verbose_name = "Laudo metabólico"
        verbose_name_plural = "Laudos metabólicos"

    def __str__(self) -> str:
        return f"Laudo - {self.simulacao_refeicao.identificador_sessao}"

    def compilar_laudo_comparativo(self) -> "LaudoMetabolico":
        eta, _ = CalculoETA.objects.get_or_create(simulacao_refeicao=self.simulacao_refeicao)
        cardio, _ = ScoreRiscoCardio.objects.get_or_create(simulacao_refeicao=self.simulacao_refeicao)
        disbiose, _ = MarcadorDisbiose.objects.get_or_create(simulacao_refeicao=self.simulacao_refeicao)

        eta.calcular_depreciacao_eta()
        cardio.calcular_score_cumulativo()
        disbiose.mapear_perturbacao_microbiota()

        if cardio.pontuacao_risco >= 70 or disbiose.risco_permeabilidade == "Alto":
            self.classe_alerta_css = "alert-danger"
        elif cardio.pontuacao_risco >= 35 or disbiose.risco_permeabilidade == "Moderado":
            self.classe_alerta_css = "alert-warning"
        else:
            self.classe_alerta_css = "alert-success"

        alimentos = ", ".join(item.alimento.nome for item in self.simulacao_refeicao.itens.select_related("alimento"))
        self.texto_sintese = (
            f"Simulação educativa composta por: {alimentos}. "
            f"Peso total: {self.simulacao_refeicao.peso_total_g:.0f}g. "
            f"ETA basal estimado: {eta.eta_basal_kcal:.2f} kcal; ETA final: {eta.etapa_final_kcal:.2f} kcal "
            f"(queda estimada de {eta.percentual_queda:.1f}%). "
            f"Score cardiovascular: {cardio.pontuacao_risco}/100, potencial {cardio.potencial_aterogenico}. "
            f"Microbiota: risco {disbiose.risco_permeabilidade}. {disbiose.descricao_alerta}"
        )
        self.save()
        return self


class RelatorioExportavel(models.Model):
    """RF15 - Exportação de diagnóstico metabólico em HTML imprimível."""

    laudo_metabolico = models.ForeignKey(LaudoMetabolico, on_delete=models.CASCADE, related_name="exportacoes")
    formato_saida = models.CharField(max_length=10, default="HTML")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relatório exportável"
        verbose_name_plural = "Relatórios exportáveis"
        ordering = ["-criado_em"]

    def gerar_documento_html(self) -> str:
        laudo = self.laudo_metabolico
        simulacao = laudo.simulacao_refeicao
        itens_html = "".join(
            f"<li>{item.quantidade_g:g}g - {item.alimento.nome} ({item.alimento.categoria_nova})</li>"
            for item in simulacao.itens.select_related("alimento")
        )
        return f"""<!doctype html>
<html lang='pt-br'>
<head>
  <meta charset='utf-8'>
  <title>Relatório metabólico</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #152019; }}
    .box {{ border: 1px solid #d8e2dc; border-radius: 14px; padding: 20px; }}
    h1 {{ color: #234f32; }}
    @media print {{ button {{ display: none; }} body {{ margin: 12mm; }} }}
  </style>
</head>
<body>
  <button onclick="window.print()">Imprimir / salvar PDF</button>
  <h1>Diagnóstico metabólico estruturado</h1>
  <div class='box'>
    <p><strong>Sessão:</strong> {simulacao.identificador_sessao}</p>
    <p><strong>Data:</strong> {simulacao.data_simulacao:%d/%m/%Y %H:%M}</p>
    <p><strong>Peso total:</strong> {simulacao.peso_total_g:.0f}g</p>
    <h2>Itens do prato virtual</h2>
    <ul>{itens_html}</ul>
    <h2>Síntese</h2>
    <p>{laudo.texto_sintese}</p>
  </div>
</body>
</html>"""

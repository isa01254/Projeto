from django.contrib import admin
from .models import (
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

admin.site.site_header = "MARELLA"
admin.site.site_title = "MARELLA"
admin.site.index_title = "Matriz de Análise de Rótulos, Elementos e Listas Alimentares"


class AlimentoAditivoInline(admin.TabularInline):
    model = AlimentoAditivo
    extra = 1


class ItemRefeicaoInline(admin.TabularInline):
    model = ItemRefeicao
    extra = 1


class CalculoETAInline(admin.StackedInline):
    model = CalculoETA
    extra = 0


class ScoreRiscoCardioInline(admin.StackedInline):
    model = ScoreRiscoCardio
    extra = 0


class MarcadorDisbioseInline(admin.StackedInline):
    model = MarcadorDisbiose
    extra = 0


class LaudoMetabolicoInline(admin.StackedInline):
    model = LaudoMetabolico
    extra = 0


@admin.register(ConsistenciaFisica)
class ConsistenciaFisicaAdmin(admin.ModelAdmin):
    list_display = ("tipo_textura", "esforco_mastigatorio")
    search_fields = ("tipo_textura", "esforco_mastigatorio")


@admin.register(AditivoAlimentar)
class AditivoAlimentarAdmin(admin.ModelAdmin):
    list_display = ("nome_quimico", "funcao_tecnologica", "grau_risco")
    list_filter = ("grau_risco", "funcao_tecnologica")
    search_fields = ("nome_quimico", "funcao_tecnologica", "impacto_fisiologico")


@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria_nova", "energia_kcal", "porcao_g", "indice_integridade")
    list_filter = ("categoria_nova", "consistencia")
    search_fields = ("nome", "observacao_metabolica")
    inlines = [AlimentoAditivoInline]


@admin.register(AlimentoAditivo)
class AlimentoAditivoAdmin(admin.ModelAdmin):
    list_display = ("alimento", "aditivo", "observacao")
    list_filter = ("aditivo__grau_risco", "aditivo__funcao_tecnologica")
    search_fields = ("alimento__nome", "aditivo__nome_quimico")


@admin.register(SimulacaoRefeicao)
class SimulacaoRefeicaoAdmin(admin.ModelAdmin):
    list_display = ("identificador_sessao", "data_simulacao", "peso_total_g")
    readonly_fields = ("identificador_sessao", "data_simulacao", "peso_total_g")
    inlines = [ItemRefeicaoInline, CalculoETAInline, ScoreRiscoCardioInline, MarcadorDisbioseInline, LaudoMetabolicoInline]


@admin.register(ItemRefeicao)
class ItemRefeicaoAdmin(admin.ModelAdmin):
    list_display = ("simulacao_refeicao", "alimento", "quantidade_g")
    search_fields = ("alimento__nome", "simulacao_refeicao__identificador_sessao")


@admin.register(SugestaoTroca)
class SugestaoTrocaAdmin(admin.ModelAdmin):
    list_display = ("alimento_ultraprocessado", "alimento_substituto_innatura")
    search_fields = ("alimento_ultraprocessado__nome", "alimento_substituto_innatura__nome")


@admin.register(CalculoETA)
class CalculoETAAdmin(admin.ModelAdmin):
    list_display = ("simulacao_refeicao", "eta_basal_kcal", "etapa_final_kcal", "percentual_queda")


@admin.register(ScoreRiscoCardio)
class ScoreRiscoCardioAdmin(admin.ModelAdmin):
    list_display = ("simulacao_refeicao", "pontuacao_risco", "potencial_aterogenico")


@admin.register(MarcadorDisbiose)
class MarcadorDisbioseAdmin(admin.ModelAdmin):
    list_display = ("simulacao_refeicao", "risco_permeabilidade")


@admin.register(LaudoMetabolico)
class LaudoMetabolicoAdmin(admin.ModelAdmin):
    list_display = ("simulacao_refeicao", "classe_alerta_css")
    search_fields = ("texto_sintese",)


@admin.register(RelatorioExportavel)
class RelatorioExportavelAdmin(admin.ModelAdmin):
    list_display = ("laudo_metabolico", "formato_saida", "criado_em")

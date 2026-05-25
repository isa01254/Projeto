from django.contrib import admin
from .models import (
    ConsistenciaFisica, AditivoAlimentare, Alimento, AlimentoAditivo,
    SimulacaoRefeicoe, ItemRefeicoe, Calculo, RiscoCardiaco,
    MarcadorDisbiose, SugestaoTroca, LaudoMetabolico, Relatorio
)

# ==========================================
# Inlines (Para editar tabelas filhas dentro da tela do pai)
# ==========================================

class AlimentoAditivoInline(admin.TabularInline):
    model = AlimentoAditivo
    extra = 1

class ItemRefeicaoInline(admin.TabularInline):
    model = ItemRefeicoe
    extra = 1

class CalculoETAInline(admin.StackedInline):
    model = Calculo

class ScoreRiscoCardioInline(admin.StackedInline):
    model = RiscoCardiaco

class MarcadorDisbioseInline(admin.StackedInline):
    model = MarcadorDisbiose

class LaudoMetabolicoInline(admin.StackedInline):
    model = LaudoMetabolico


# ==========================================
# Cadastros Base (Catálogos e Referências)
# ==========================================

@admin.register(ConsistenciaFisica)
class ConsistenciaFisicaAdmin(admin.ModelAdmin):
    list_display = ('tipo_textura', 'esforco_mastigatorio')
    search_fields = ('tipo_textura',)

@admin.register(AditivoAlimentare)
class AditivoAlimentarAdmin(admin.ModelAdmin):
    list_display = ('nome_quimico', 'funcao_tecnologica', 'grau_risco')
    list_filter = ('grau_risco', 'funcao_tecnologica')
    search_fields = ('nome_quimico',)

@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria_nova', 'energia_kcal', 'porcao_g')
    list_filter = ('categoria_nova',)
    search_fields = ('nome',)
    inlines = [AlimentoAditivoInline] # Permite adicionar aditivos diretamente na tela do Alimento

@admin.register(AlimentoAditivo)
class AlimentoAditivoAdmin(admin.ModelAdmin):
    list_display = ('alimento', 'aditivo')
    list_filter = ('aditivo__grau_risco',)
    search_fields = ('alimento__nome', 'aditivo__nome_quimico')

@admin.register(SugestaoTroca)
class SugestaoTrocaAdmin(admin.ModelAdmin):
    list_display = ('alimento_ultraprocessado', 'alimento_substituto_innatura')
    search_fields = ('alimento_ultraprocessado__nome', 'alimento_substituto_innatura__nome')


# ==========================================
# Operacional (Simulações e Laudos)
# ==========================================

@admin.register(SimulacaoRefeicoe)
class SimulacaoRefeicaoAdmin(admin.ModelAdmin):
    list_display = ('identificador_sessao', 'data_simulacao', 'peso_total_g')
    readonly_fields = ('identificador_sessao', 'peso_total_g')
    # Adicionando os itens e resultados diretamente na tela da Simulação para facilitar a visualização
    inlines = [
        ItemRefeicaoInline, 
        CalculoETAInline, 
        ScoreRiscoCardioInline, 
        MarcadorDisbioseInline, 
        LaudoMetabolicoInline
    ]

@admin.register(ItemRefeicoe)
class ItemRefeicaoAdmin(admin.ModelAdmin):
    list_display = ('simulacao_refeicao', 'alimento', 'quantidade_g')
    search_fields = ('alimento__nome', 'simulacao_refeicao__identificador_sessao')

@admin.register(LaudoMetabolico)
class LaudoMetabolicoAdmin(admin.ModelAdmin):
    list_display = ('simulacao_refeicao', 'classe_alerta_css')
    search_fields = ('simulacao_refeicao__identificador_sessao',)

@admin.register(Relatorio)
class RelatorioExportavelAdmin(admin.ModelAdmin):
    list_display = ('laudo_metabolico', 'formato_saida')

# Registrando os modelos auxiliares isoladamente, caso precise editá-eles fora da Simulação
admin.site.register(Calculo)
admin.site.register(RiscoCardiaco)
admin.site.register(MarcadorDisbiose)
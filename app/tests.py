from django.test import TestCase
from .models import AditivoAlimentar, Alimento, AlimentoAditivo, CalculoETA, ConsistenciaFisica, ItemRefeicao, SimulacaoRefeicao


class RegrasDeIntegridadeTest(TestCase):
    def setUp(self):
        self.liquida = ConsistenciaFisica.objects.create(tipo_textura="Líquida", esforco_mastigatorio="Baixo")
        self.solida = ConsistenciaFisica.objects.create(tipo_textura="Sólida", esforco_mastigatorio="Alto")
        self.fosfato = AditivoAlimentar.objects.create(nome_quimico="Fosfato de sódio", funcao_tecnologica="Estabilizador", grau_risco="Alto")

    def test_ultraprocessado_com_aditivo_tem_menor_integridade(self):
        arroz = Alimento.objects.create(nome="Arroz", categoria_nova=Alimento.NOVA_1, energia_kcal=130, porcao_g=100, consistencia=self.solida)
        refri = Alimento.objects.create(nome="Refrigerante", categoria_nova=Alimento.NOVA_4, energia_kcal=42, porcao_g=100, consistencia=self.liquida)
        AlimentoAditivo.objects.create(alimento=refri, aditivo=self.fosfato)
        self.assertGreater(arroz.indice_integridade(), refri.indice_integridade())

    def test_eta_aplica_queda_proporcional_a_ultraprocessados(self):
        refri = Alimento.objects.create(nome="Refrigerante", categoria_nova=Alimento.NOVA_4, energia_kcal=42, porcao_g=100, consistencia=self.liquida)
        simulacao = SimulacaoRefeicao.objects.create()
        ItemRefeicao.objects.create(simulacao_refeicao=simulacao, alimento=refri, quantidade_g=200)
        eta = CalculoETA.objects.create(simulacao_refeicao=simulacao)
        eta.calcular_depreciacao_eta()
        self.assertEqual(eta.percentual_queda, 30.0)
        self.assertGreater(eta.eta_basal_kcal, eta.etapa_final_kcal)

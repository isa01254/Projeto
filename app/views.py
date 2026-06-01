from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AditivoBuscaForm, CatalogoFiltroForm, ComparacaoForm, ItemRefeicaoForm
from .models import (
    AditivoAlimentar,
    Alimento,
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


def home(request):
    alimentos = Alimento.objects.prefetch_related("aditivos")
    contexto = {
        "total_alimentos": alimentos.count(),
        "total_aditivos": AditivoAlimentar.objects.count(),
        "total_ultraprocessados": alimentos.filter(categoria_nova=Alimento.NOVA_4).count(),
        "total_simulacoes": SimulacaoRefeicao.objects.count(),
        "exemplos": alimentos.order_by("categoria_nova", "nome")[:6],
        "funcionalidades_resumo": lista_funcionalidades()[:6],
    }
    return render(request, "app/index.html", contexto)


def lista_funcionalidades():
    return [
        {"codigo": "RF01", "nome": "Classificação NOVA do alimento", "link": "catalogo", "status": "Implementado"},
        {"codigo": "RF02", "nome": "Mapeamento de aditivos químicos", "link": "aditivos", "status": "Implementado"},
        {"codigo": "RF03", "nome": "Associação alimento-aditivo", "link": "catalogo", "status": "Implementado"},
        {"codigo": "RF04", "nome": "Consistência física e mastigação", "link": "consistencias", "status": "Implementado"},
        {"codigo": "RF05", "nome": "Prato virtual/simulação", "link": "simulacao", "status": "Implementado"},
        {"codigo": "RF06", "nome": "Itens integrados à refeição", "link": "simulacao", "status": "Implementado"},
        {"codigo": "RF07", "nome": "Cálculo de ETA", "link": "laudo", "status": "Implementado"},
        {"codigo": "RF08", "nome": "Score cardiovascular", "link": "laudo", "status": "Implementado"},
        {"codigo": "RF09", "nome": "Marcador de microbiota/disbiose", "link": "laudo", "status": "Implementado"},
        {"codigo": "RF10", "nome": "Sugestão de substituição inteligente", "link": "trocas", "status": "Implementado"},
        {"codigo": "RF11", "nome": "Laudo clínico-nutricional", "link": "laudo", "status": "Implementado"},
        {"codigo": "RF12", "nome": "Catálogo público de alimentos", "link": "catalogo", "status": "Implementado"},
        {"codigo": "RF13", "nome": "Painel toxicológico de aditivos", "link": "aditivos", "status": "Implementado"},
        {"codigo": "RF14", "nome": "Validação de simulação e formulários", "link": "simulacao", "status": "Implementado"},
        {"codigo": "RF15", "nome": "Exportação de relatório HTML", "link": "exportar_relatorio", "status": "Implementado"},
        {"codigo": "LOGIN", "nome": "Autenticação de usuário", "link": "login", "status": "Implementado"},
    ]


def painel_funcionalidades(request):
    contexto = {
        "funcionalidades": lista_funcionalidades(),
        "total": len(lista_funcionalidades()),
        "alimentos": Alimento.objects.count(),
        "aditivos": AditivoAlimentar.objects.count(),
    }
    return render(request, "app/funcionalidades.html", contexto)


def dashboard(request):
    categorias = []
    for valor, rotulo in Alimento.NOVA_CHOICES:
        categorias.append({"categoria": valor, "rotulo": rotulo, "total": Alimento.objects.filter(categoria_nova=valor).count()})
    alimentos = Alimento.objects.prefetch_related("aditivos")
    indices = [a.indice_integridade() for a in alimentos]
    contexto = {
        "categorias": categorias,
        "total_alimentos": Alimento.objects.count(),
        "total_aditivos": AditivoAlimentar.objects.count(),
        "total_consistencias": ConsistenciaFisica.objects.count(),
        "media_integridade": round(sum(indices) / len(indices), 1) if indices else 0,
        "alto_risco": AditivoAlimentar.objects.filter(grau_risco=AditivoAlimentar.RISCO_ALTO).count(),
        "ultimas_simulacoes": SimulacaoRefeicao.objects.order_by("-data_simulacao")[:5],
    }
    return render(request, "app/dashboard.html", contexto)


def catalogo_alimentos(request):
    form = CatalogoFiltroForm(request.GET or None)
    alimentos = Alimento.objects.select_related("consistencia").prefetch_related("aditivos")

    if form.is_valid():
        busca = form.cleaned_data.get("busca")
        categoria = form.cleaned_data.get("categoria_nova")
        if busca:
            alimentos = alimentos.filter(Q(nome__icontains=busca) | Q(observacao_metabolica__icontains=busca))
        if categoria:
            alimentos = alimentos.filter(categoria_nova=categoria)

    return render(request, "app/catalogo.html", {"form": form, "alimentos": alimentos})


def painel_aditivos(request):
    form = AditivoBuscaForm(request.GET or None)
    aditivos = AditivoAlimentar.objects.all()
    termo = ""
    if form.is_valid():
        termo = form.cleaned_data.get("termo", "")
        if termo:
            aditivos = aditivos.filter(
                Q(nome_quimico__icontains=termo)
                | Q(funcao_tecnologica__icontains=termo)
                | Q(impacto_fisiologico__icontains=termo)
            )
    return render(request, "app/aditivos.html", {"form": form, "aditivos": aditivos, "termo": termo})


def consistencias(request):
    dados = ConsistenciaFisica.objects.all()
    return render(request, "app/consistencias.html", {"consistencias": dados})


def sugestoes_troca(request):
    sugestoes = SugestaoTroca.objects.select_related("alimento_ultraprocessado", "alimento_substituto_innatura")
    ultraprocessados_sem_troca = Alimento.objects.filter(categoria_nova=Alimento.NOVA_4).exclude(
        trocas_como_ruim__isnull=False
    )
    return render(
        request,
        "app/trocas.html",
        {"sugestoes": sugestoes, "ultraprocessados_sem_troca": ultraprocessados_sem_troca},
    )


def historico_simulacoes(request):
    simulacoes = SimulacaoRefeicao.objects.prefetch_related("itens", "itens__alimento").order_by("-data_simulacao")[:30]
    return render(request, "app/historico.html", {"simulacoes": simulacoes})


def texto_comparativo(alimento_a: Alimento, alimento_b: Alimento) -> str:
    diff = alimento_a.indice_integridade() - alimento_b.indice_integridade()
    if diff > 0:
        melhor = alimento_a
        pior = alimento_b
    elif diff < 0:
        melhor = alimento_b
        pior = alimento_a
    else:
        return "Os dois alimentos ficaram com o mesmo Índice de Integridade. Compare a presença de aditivos e a consistência para uma análise qualitativa mais fina."

    return (
        f"{melhor.nome} apresenta maior integridade alimentar na regra do sistema. "
        f"A diferença em relação a {pior.nome} ocorre principalmente por categoria NOVA, aditivos cadastrados e esforço mastigatório."
    )


def comparar_alimentos(request):
    resultado = None
    form = ComparacaoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        alimento_a = form.cleaned_data["alimento_a"]
        alimento_b = form.cleaned_data["alimento_b"]
        resultado = {
            "a": alimento_a,
            "b": alimento_b,
            "sintese": texto_comparativo(alimento_a, alimento_b),
            "sugestao_a": SugestaoTroca.executar_substituicao_inteligente(alimento_a),
            "sugestao_b": SugestaoTroca.executar_substituicao_inteligente(alimento_b),
        }
    return render(request, "app/comparar.html", {"form": form, "resultado": resultado})


def obter_simulacao_ativa(request) -> SimulacaoRefeicao:
    simulacao_id = request.session.get("simulacao_id")
    if simulacao_id:
        simulacao = SimulacaoRefeicao.objects.filter(id=simulacao_id).first()
        if simulacao:
            return simulacao
    simulacao = SimulacaoRefeicao.objects.create()
    request.session["simulacao_id"] = simulacao.id
    return simulacao


def calcular_componentes(simulacao: SimulacaoRefeicao):
    eta, _ = CalculoETA.objects.get_or_create(simulacao_refeicao=simulacao)
    cardio, _ = ScoreRiscoCardio.objects.get_or_create(simulacao_refeicao=simulacao)
    disbiose, _ = MarcadorDisbiose.objects.get_or_create(simulacao_refeicao=simulacao)
    eta.calcular_depreciacao_eta()
    cardio.calcular_score_cumulativo()
    disbiose.mapear_perturbacao_microbiota()
    laudo, _ = LaudoMetabolico.objects.get_or_create(simulacao_refeicao=simulacao)
    laudo.compilar_laudo_comparativo()
    return eta, cardio, disbiose, laudo


@login_required
def simulacao_refeicao(request):
    simulacao = obter_simulacao_ativa(request)

    if request.method == "POST" and request.POST.get("acao") == "limpar":
        simulacao.delete()
        request.session.pop("simulacao_id", None)
        messages.info(request, "Prato virtual limpo. Uma nova simulação foi iniciada.")
        return redirect("simulacao")

    form = ItemRefeicaoForm(request.POST or None)
    if request.method == "POST" and request.POST.get("acao") == "adicionar" and form.is_valid():
        item = form.save(commit=False)
        item.simulacao_refeicao = simulacao
        item.save()
        simulacao.calcular_peso_total()
        messages.success(request, f"{item.alimento.nome} foi adicionado ao prato virtual.")
        return redirect("simulacao")

    if request.method == "POST" and request.POST.get("acao") == "gerar":
        if not simulacao.possui_itens():
            messages.error(request, "Não é possível gerar laudo com a refeição vazia.")
            return redirect("simulacao")
        calcular_componentes(simulacao)
        messages.success(request, "Laudo metabólico gerado com sucesso.")
        return redirect("laudo")

    itens = simulacao.itens.select_related("alimento", "alimento__consistencia").prefetch_related("alimento__aditivos")
    contexto = {
        "form": form,
        "simulacao": simulacao,
        "itens": itens,
        "energia_total": simulacao.energia_total(),
        "sugestoes": [SugestaoTroca.executar_substituicao_inteligente(item.alimento) for item in itens if item.alimento.categoria_nova == Alimento.NOVA_4],
    }
    return render(request, "app/simulacao.html", contexto)


@login_required
def laudo_simulacao(request):
    simulacao = obter_simulacao_ativa(request)
    if not simulacao.possui_itens():
        messages.error(request, "Adicione ao menos um alimento antes de consultar o laudo.")
        return redirect("simulacao")
    eta, cardio, disbiose, laudo = calcular_componentes(simulacao)
    return render(
        request,
        "app/laudo.html",
        {"simulacao": simulacao, "eta": eta, "cardio": cardio, "disbiose": disbiose, "laudo": laudo},
    )


@login_required
def exportar_relatorio(request):
    simulacao = obter_simulacao_ativa(request)
    if not simulacao.possui_itens():
        messages.error(request, "Não há itens para exportar.")
        return redirect("simulacao")
    _, _, _, laudo = calcular_componentes(simulacao)
    relatorio = RelatorioExportavel.objects.create(laudo_metabolico=laudo, formato_saida="HTML")
    return HttpResponse(relatorio.gerar_documento_html(), content_type="text/html; charset=utf-8")


@login_required
def remover_item(request, item_id):
    item = get_object_or_404(ItemRefeicao, id=item_id, simulacao_refeicao_id=request.session.get("simulacao_id"))
    item.delete()
    obter_simulacao_ativa(request).calcular_peso_total()
    messages.info(request, "Item removido do prato virtual.")
    return redirect("simulacao")

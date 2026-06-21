from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    AditivoBuscaForm,
    CadastroUsuarioForm,
    CatalogoFiltroForm,
    ComparacaoForm,
    ItemRefeicaoForm,
)
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
    }
    return render(request, "index.html", contexto)


def cadastro_usuario(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = CadastroUsuarioForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "Conta criada com sucesso. Você já está conectado.")

        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        return redirect("dashboard")

    return render(request, "cadastro.html", {"form": form, "next": next_url})


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
    return render(request, "dashboard.html", contexto)


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

    return render(request, "catalogo.html", {"form": form, "alimentos": alimentos})


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
    return render(request, "aditivos.html", {"form": form, "aditivos": aditivos, "termo": termo})


def consistencias(request):
    dados = ConsistenciaFisica.objects.all()
    return render(request, "consistencias.html", {"consistencias": dados})


def sugestoes_troca(request):
    sugestoes = SugestaoTroca.objects.select_related("alimento_ultraprocessado", "alimento_substituto_innatura")
    ultraprocessados_sem_troca = Alimento.objects.filter(categoria_nova=Alimento.NOVA_4).exclude(
        trocas_como_ruim__isnull=False
    )
    return render(
        request,
        "trocas.html",
        {"sugestoes": sugestoes, "ultraprocessados_sem_troca": ultraprocessados_sem_troca},
    )


def historico_simulacoes(request):
    simulacoes = SimulacaoRefeicao.objects.prefetch_related("itens", "itens__alimento").order_by("-data_simulacao")[:30]
    return render(request, "historico.html", {"simulacoes": simulacoes})


def texto_comparativo(alimento_a: Alimento, alimento_b: Alimento) -> str:
    diff = alimento_a.indice_integridade() - alimento_b.indice_integridade()
    if diff > 0:
        melhor = alimento_a
        pior = alimento_b
    elif diff < 0:
        melhor = alimento_b
        pior = alimento_a
    else:
        return "Os dois alimentos ficaram com a mesma pontuação. Compare os componentes do rótulo e a consistência para escolher com mais clareza."

    return (
        f"{melhor.nome} ficou melhor na leitura do sistema. "
        f"A diferença em relação a {pior.nome} ocorre principalmente pelo tipo do alimento, componentes cadastrados e esforço de mastigação."
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
    return render(request, "comparar.html", {"form": form, "resultado": resultado})


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
            messages.error(request, "Não é possível gerar resumo com a refeição vazia.")
            return redirect("simulacao")
        calcular_componentes(simulacao)
        messages.success(request, "Resumo da refeição gerado com sucesso.")
        return redirect("laudo")

    itens = simulacao.itens.select_related("alimento", "alimento__consistencia").prefetch_related("alimento__aditivos")
    contexto = {
        "form": form,
        "simulacao": simulacao,
        "itens": itens,
        "energia_total": simulacao.energia_total(),
        "sugestoes": [SugestaoTroca.executar_substituicao_inteligente(item.alimento) for item in itens if item.alimento.categoria_nova == Alimento.NOVA_4],
    }
    return render(request, "simulacao.html", contexto)


@login_required
def laudo_simulacao(request):
    simulacao = obter_simulacao_ativa(request)
    if not simulacao.possui_itens():
        messages.error(request, "Adicione ao menos um alimento antes de consultar o resumo.")
        return redirect("simulacao")
    eta, cardio, disbiose, laudo = calcular_componentes(simulacao)
    return render(
        request,
        "laudo.html",
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
def perfil(request):
    return render(request, "perfil.html")


@login_required
@require_POST
def remover_item(request, item_id):
    item = get_object_or_404(ItemRefeicao, id=item_id, simulacao_refeicao_id=request.session.get("simulacao_id"))
    item.delete()
    obter_simulacao_ativa(request).calcular_peso_total()
    messages.info(request, "Item removido do prato virtual.")
    return redirect("simulacao")

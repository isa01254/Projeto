from django import forms

from .models import AditivoAlimentar, Alimento, ItemRefeicao


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class CatalogoFiltroForm(BootstrapFormMixin, forms.Form):
    busca = forms.CharField(
        label="Buscar alimento",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nome ou observação"}),
    )
    categoria_nova = forms.ChoiceField(
        label="Tipo de alimento",
        required=False,
        choices=[("", "Todos os tipos")] + list(Alimento.NOVA_CHOICES),
    )


class AditivoBuscaForm(BootstrapFormMixin, forms.Form):
    termo = forms.CharField(
        label="Buscar componente",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nome, uso ou observação"}),
    )


class ComparacaoForm(BootstrapFormMixin, forms.Form):
    alimento_a = forms.ModelChoiceField(
        label="Primeiro alimento",
        queryset=Alimento.objects.all(),
        empty_label="Selecione um alimento",
    )
    alimento_b = forms.ModelChoiceField(
        label="Segundo alimento",
        queryset=Alimento.objects.all(),
        empty_label="Selecione outro alimento",
    )

    def clean(self):
        cleaned_data = super().clean()
        alimento_a = cleaned_data.get("alimento_a")
        alimento_b = cleaned_data.get("alimento_b")
        if alimento_a and alimento_b and alimento_a == alimento_b:
            raise forms.ValidationError("Escolha dois alimentos diferentes para comparar.")
        return cleaned_data


class ValidadorSimulacao:
    QUANTIDADE_MAXIMA_G = 2000

    @classmethod
    def validar_quantidade(cls, quantidade_g):
        if quantidade_g is None:
            raise forms.ValidationError("Informe a quantidade em gramas.")
        if quantidade_g <= 0:
            raise forms.ValidationError("A quantidade precisa ser maior que zero.")
        if quantidade_g > cls.QUANTIDADE_MAXIMA_G:
            raise forms.ValidationError("Use uma quantidade menor ou igual a 2000g.")
        return quantidade_g

    @staticmethod
    def validar_alimento(alimento):
        if alimento is None:
            raise forms.ValidationError("Selecione um alimento para a simulação.")
        return alimento


class ItemRefeicaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ItemRefeicao
        fields = ["alimento", "quantidade_g"]
        labels = {
            "alimento": "Alimento",
            "quantidade_g": "Quantidade (g)",
        }
        widgets = {
            "quantidade_g": forms.NumberInput(attrs={"min": "1", "step": "1"}),
        }

    def clean_alimento(self):
        return ValidadorSimulacao.validar_alimento(self.cleaned_data.get("alimento"))

    def clean_quantidade_g(self):
        return ValidadorSimulacao.validar_quantidade(self.cleaned_data.get("quantidade_g"))

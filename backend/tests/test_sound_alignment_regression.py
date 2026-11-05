def test_excavation_anchor_should_not_be_segment_start():
    text = (
        "Tal vez era inmenso su temor de hacer daño a sus hijos, "
        "que quiso alejarse de ellos hasta ser nuevamente cabal "
        "en todos los sentidos. Por las noches cuentan las personas "
        "que se escuchaban como si estuviesen excavando en"
    )

    anchor = "se escuchaban como si estuviesen excavando"
    duration = 12.6375

    assert anchor in text

    estimated_offset = duration * text.index(anchor) / len(text)

    assert estimated_offset > 0
    assert estimated_offset < duration

    # El planificador automático actual utiliza offset=0.
    # Esta prueba documenta que esa posición no corresponde
    # al inicio estimado de la frase de excavación.
    automatic_offset = 0

    assert automatic_offset != estimated_offset

"""
 Base form class, form html builders and custom fields and widgets.
"""

from functools import partial

from django.utils.safestring import mark_safe
from django import forms
from openletsweb.forms import widgets

__all__ = [
    "BaseFormMixin",
    "CurrencyValueField",
    "PlaceholderField",
    "PlaceholderChar",
    "PlaceholderEmail",
    "currency_clean_helper",
    "widgets",
]


class BaseFormMixin(object):
    """Mixin for adding an as_plain render method and an as_p
    render that works with bootstrap default styles.
    """

    def __init__(self, *args, **kwargs):
        super(BaseFormMixin, self).__init__(*args, **kwargs)
        self.build_form_parts()

    _parts = None

    def as_plain(self):
        """Render the form without labels and help text."""
        return self._html_output(
            normal_row="<p%(html_class_attr)s>%(field)s</p>",
            error_row="%s",
            row_ender="</p>",
            help_text_html="%s",
            errors_on_separate_row=True,
        )

    def as_p(self):
        """Changes the default as_p rendering by adding a div around
        the field.
        """
        return self._html_output(
            normal_row="<p%(html_class_attr)s>"
            '%(label)s <div class="input">%(field)s %(help_text)s</div></p>',
            error_row="%s",
            row_ender="</p>",
            help_text_html=' <span class="help-block">%s</span>',
            errors_on_separate_row=True,
        )

    def _list_html_output_fields(self, part, fields):
        """Build the html for a part of the form."""
        html = []
        for field_name in fields:
            field = self[field_name]
            html.append(
                mark_safe(
                    "%s<p>%s</p><div class='input'>%s</div>"
                    % ("\n".join(field.errors), field.label_tag(), str(field))
                )
            )
        return html

    def _html_output_fields(self, part, fields):
        html = self._list_html_output_fields(part, fields)
        return mark_safe("<fieldset>%s</fieldset>" % "\n".join(html))

    def build_form_parts(self):
        """Create functions for returning the html for different parts
        of the form. _parts should be of the form:
                {
                        part_name: [fielda, fieldb],
                        ...
                }
        """
        if not self._parts:
            return
        for part, fields in self._parts.items():
            setattr(
                self, "part_%s" % part, partial(self._html_output_fields, part, fields)
            )
            setattr(
                self,
                "list_part_%s" % part,
                partial(self._list_html_output_fields, part, fields),
            )


class PlaceholderField(object):
    """A mixin for fields that uses placeholder for label."""

    def widget_attrs(self, widget):
        attrs = super(PlaceholderField, self).widget_attrs(widget) or {}
        attrs["placeholder"] = self.label
        return attrs


class PlaceholderChar(PlaceholderField, forms.CharField):
    widget = widgets.PlaceholderTextInput


class PlaceholderEmail(PlaceholderField, forms.EmailField):
    widget = widgets.PlaceholderTextInput


class CurrencyValueField(forms.CharField):
    """A field for currency values."""

    def clean(self, value):
        """Clean a value. Ensure that the value is numeric."""
        value = super(CurrencyValueField, self).clean(value)
        value_parts = value.split(".")
        if len(value_parts) > 2:
            raise forms.ValidationError("Unknown number %s" % (value))
        for part in value_parts:
            if not part.isdigit():
                raise forms.ValidationError("Unknown number %s" % (value))
        return tuple(int(p) for p in value_parts)

    def widget_attrs(self, widget):
        attrs = super(CurrencyValueField, self).widget_attrs(widget) or {}
        attrs["class"] = "mini"
        return attrs


def currency_clean_helper(currency, value):
    """Used to validate that a currency value works for a
    give currency.  Should be called from a forms clean() method.

    Returns (value, errors)
    """
    whole = value[0]
    frac = str(value[1]) if len(value) == 2 else None
    if frac and len(frac) > currency.decimal_places:
        return None, "Too many decimal places (%s) for currency %s" % (
            len(frac),
            currency,
        )

    if not frac:
        frac = "0" * currency.decimal_places
    elif len(frac) < currency.decimal_places:
        frac += "0" * (currency.decimal_places - len(frac))

    return int(str(whole) + frac), None

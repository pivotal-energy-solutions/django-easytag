django-easytag
==============

A templatetag utility to greatly simplify the design of block-style tags

EasyTag is a ``template.Node`` subclass that adds some automatic mechanisms which greatly simplify the common block-style tasks.

Subclasses should set the ``name`` class attribute, which will be the name used in templates.  This helps save you the trouble of writing a separate compiler function just to wrap it in the ``@register.tag`` decorator.

Registering the tag becomes very simple:

```python
# A little wordy, if you've named your local library object "register", as is recommended:
MyTagClass.register_tag(register)
    
# This is basically the ``register.tag`` decorator, and looks more like a normal
# registration.  +1 if you're all about vanilla and no magic.
register.tag(MyTagClass.name, MyTagClass.parser)
```

A simpler ``register()`` method cannot be added to EasyTag, since EasyTag won't have an active
reference to your tag's specific Library instance, so it would be registered to the wrong
library at runtime.

If ``end_tag`` is True, this tag will automatically parse to a matching ``{% end{name} %}`` tag.
If ``end_tag`` is a string, it will be taken as-is for the end-block tag.  It won't add the
"end" prefix either, so pick a smart name!

EasyTag enables automatic forwarding of parameters sent to the tag to a method on your tag.  The
method should match the tag's ``name`` attribute, and it is treated like a render() method.  The
only difference is that you get the ``nodelist`` parameter, which holds all of the content
wrapped by your tag:

```python
class MyTag(EasyTag):
    # This tag doesn't do anything but render the wrapped contents normally, but it
    # demonstrates what the format should look like in its simplest form.
    name = "my_tag"

    def my_tag(self, context, nodelist):
        return nodelist.render(context)
```

In Django parlance, a "nodelist" is a collection of template pieces that all know how to render
themselves, including chunks of plain text.

Your tag's method requires ``context`` and ``nodelist``, but you can add any number of normal
function arguments to its signature, exactly like a Django ``simple_tag``.  The parser will
inspect you method and make sure there are no missing or extra arguments, creating a really
simple interface for sending parameters to the tag:

```python
# Handler inside of the MyTag class
def my_tag(self, context, nodelist, myflag=False):
    content = nodelist.render(context)
    if myflag is True:
        content = "<div class='hidden'>%s</div>" % (content,)
    return content
```

```html
# In template:
{# With optional var specified: #}
{% mytag myflag=True %} Some content {% endmytag %}

{# Without option var: #}
{% mytag %} Other content {% endmytag %}
```

Tag handlers support all the fancy stuff: required params, the *args catch-all, and the
**kwargs catch-all.

``intermediate_tags`` is a list of strings that acts as a declaration of all possible
intermediate tag names that can show up in the body of your main tag.  For example, if you use
``intermediate_tags = ["unless"]``, you could write something like this in your templates:

```html
{% mytag myflag=True %}
    some content
{% unless %}
    secondary content
{% endmytag %}
```

By default, both of these sections are parsed and rendered, but they are handed off to separate
methods on your tag class for processing, allowing you to dynamically decide if or how to render
the sibling branches.  In the following example, you a variable is used to toggle which arm of
the compound tag is rendered:

```python
class MyTag(EasyTag):
    # ...
    def mytag(self, context, nodelist, myflag=False):
        self.myflag = myflag
        if self.myflag:
            return ''
        return nodelist.render(context)
    
    def unless(self, context, nodelist):
        if self.myflag:
            return nodelist.render(context)
        return ''
```

Because the ``mytag`` handler is always executed first, you can rely on ``self.myflag`` being
set by the time the ``unless`` handler is called.

Note that you can have more than one type of intermediate tag, and they can appear in any order,
and even appear multiple times:

```html
{% mytag %}
    Header content, rendered by the main "mytag" handler
    {% section header="First" %}
        Some content, to be rendered by the "section" handler
    {% section header="Second" is_required=someflag %}
        More content, also rendered by the "section" handler
    {% footer %}
        Content, possibly only rendered if some running calculation is satisfied.
{% endmytag %}
```

django-easytag
==============

A templatetag utility to greatly simplify the design of block-style tags

EasyTag is a ``template.Node`` subclass that adds some automatic mechanisms which greatly simplify the common block-style tasks.


You can add methods to your subclass to handle any custom intermediate tag separators (think the ``for``/``empty``, ``if``/``else``).

## Basic options

### ``name``
_**Required**_

The name of the tag as it should be registered with your templatetags library.  See [Registering with the tag library](#registering-with-the-tag-library) below to see how to make use of this ``name`` attribute without having to repeat yourself.

### ``end_tag``
_boolean or str_

If ``end_tag`` is True, this tag will automatically parse to a matching ``{% end{name} %}`` tag. If ``end_tag`` is a string, it will be taken as-is for the end-block tag.  It won't add the "end" prefix either, so pick a smart name!

### ``intermediate_tags``
_list of strings_

``intermediate_tags`` is a list of strings that acts as a declaration of all possible intermediate tag names that can show up in the body of your main tag.  For example, if you use ``intermediate_tags = ["unless"]``, you could write something like this in your templates:

```html
{% my_tag %}
    some content
{% unless %}
    secondary content
{% endmytag %}
```

By default, both of these sections are parsed and rendered, but they are handed off to separate methods on your tag class for processing, allowing you to dynamically decide if or how to render the sibling branches.

You can have any number of intermediate tags, and they can appear in any order.  If you would like to enforce a particular order, you'll need to add some logic to the specific handlers to verify that some other tag came first.

## Setting up handlers for wrapped content

The beginning tag and intermediate tags will attempt to send their influenced template regions to methods on your tag class.  These methods are effectively renderers; you should return the rendered content, whether or not you are modifying anything.

The simplest case is a pass-through tag:

```python
class MyTag(EasyTag):
    name = "my_tag"

    def my_tag(self, context, nodelist):
        return nodelist.render(context)
```

Your ``my_tag`` tag should declare a method on itself named the same thing.  This is the handler that the wrapped content is sent to.  The ``context`` and ``nodelist`` parameters are required.

_Note: In Django parlance, a "nodelist" is a collection of template pieces that all know how to render themselves, including chunks of plain text._

If you have intermediate tags defined note how the definition of "wrapped content" changes:

```html
<!-- example template use -->
{% my_tag %}
    some content
{% unless %}
    secondary content
{% endmytag %}
```

The main ``my_tag`` method only receives everything up until the next intermediate block, and the intermediate block receives everything until the _next_ intermediate block or the end tag, and so on.

## Sending parameters

Exactly like the built-in django [``simple_tag``](https://docs.djangoproject.com/en/dev/howto/custom-template-tags/#django.template.Library.simple_tag), EasyTag enables automatic forwarding of parameters sent to the tag to a method on your tag.

Your tag's method requires ``context`` and ``nodelist``, but you can add any number of normal function arguments to its signature.  This includes arguments with default values, ``*args`` and ``**kwargs`` for catch-alls.  The proper errors will be raised if arguments are missing or unexpected.

Example:

```python
# Handler inside of the MyTag class
def my_tag(self, context, nodelist, myflag=False):
    content = nodelist.render(context)
    if myflag is True:
        content = "<div class='hidden'>%s</div>" % (content,)
    return content
```

```html
<!-- In template -->
{# With optional var specified: #}
{% mytag myflag=True %} Some content {% endmytag %}

{# Without option var: #}
{% mytag %} Other content {% endmytag %}
```

## Registering with the tag library

Subclasses should set the ``name`` class attribute, which will be the name used in templates.  This helps save you the trouble of writing a separate compiler function just to wrap it in the ``@register.tag`` decorator.

Registering the tag becomes very simple:

```python
# A little wordy, if you've named your local library object "register", as is recommended:
MyTagClass.register_tag(register)
    
# This is basically the ``register.tag`` decorator, and looks more like a normal
# registration.  +1 if you're all about vanilla and no magic.
register.tag(MyTagClass.name, MyTagClass.parser)
```

A simpler ``register()`` method cannot be added to EasyTag, since EasyTag won't have an active reference to your tag's specific Library instance, so it would be registered to the wrong library at runtime.

## Using variables across intermediate tags

Say you want to open your tag with some arguments, and the intermediate tags should be able to use those values as they are encountered.

For example, the target usage should look something like this:

```html
{% my_tag active_section="Second" %}
    {% section name="First" %}
        Some content
    {% section name="Second" %}
        More content
{% endmy_tag %}
```

It's simple to save the variable on the ``my_tag`` handler (although if you're modifying stateful values after storing them, though please be sure to ready about the Django documentation about templatetag [thread safety](https://docs.djangoproject.com/en/dev/howto/custom-template-tags/#thread-safety-considerations)), and once you've got that done, it's a simple matter of inspecting the values:

```python
def my_tag(self, context, nodelist, active_section=None):
    self.active_section = active_section

    # In the example template use, the nodelist was approximately empty,
    # holding only whitespace, but we should render it anyway.
    return nodelist.render(context)

def section(self, context, nodelist, name):
    wrapper = """<div class="%(active)s">%(content)</div>"""
    content = nodelist.render(context)
    if name == self.active_section:
        active_class = "active"
    else:
        active_class = ""
    return wrapper % {'active': active_class, 'content': content}
```

This works because the ``my_tag`` handler is always executed first, being the opening tag handler.

## Wrapping the entire tag output, appending, prefixing, etc

Because of the way your opening handler actually only handles the initial branch of template until the first intermediate tag, you can't use this particular spot as a way to wrap the entire output.

Instead, you should override the built-in ``render()`` method of the tag.  This method is provided by default on a ``template.Node`` object.  The ``EasyTag.render()`` implementation iterates all of your branches and concatenates their output.

Consequently, if you would like to wrap all of the output in some HTML, append markup to the end, etc, you should call ``super()`` to get the normal output, and then modify it as you see fit:

```python
def render(self, context):
    content = super(MyTag, self).render(context)
    return "<div id='wrapper'>%s</div>" % content
```

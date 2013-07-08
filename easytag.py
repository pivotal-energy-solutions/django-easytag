from inspect import getargspec
from functools import partial, wraps

from django import template
from django.template.base import parse_bits

register = template.Library()

class EasyTag(template.Node):
    """
    A ``template.Node`` subclass that adds some automatic mechanisms which greatly simplify the
    common block-style tasks.

    Subclasses should set the ``name`` class attribute, which will be the name used in templates.
    This helps save you the trouble of writing a separate compiler function just to wrap it in the
    ``@register.tag`` decorator.

    Registering the tag becomes very simple:

        # A little wordy, if you've named your local library object "register", as is recommended:
        MyTagClass.register_tag(register)

        # This is basically the ``register.tag`` decorator, and looks more like a normal
        # registration.  +1 if you're all about vanilla and no magic.
        register.tag(MyTagClass.name, MyTagClass.parser)
    
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

        class MyTag(EasyTag):
            # This tag doesn't do anything but render the wrapped contents normally, but it
            # demonstrates what the format should look like in its simplest form.
            name = "my_tag"

            def my_tag(self, context, nodelist):
                return nodelist.render(context)

    In Django parlance, a "nodelist" is a collection of template pieces that all know how to render
    themselves, including chunks of plain text.
    
    Your tag's method requires ``context`` and ``nodelist``, but you can add any number of normal
    function arguments to its signature, exactly like a Django ``simple_tag``.  The parser will
    inspect you method and make sure there are no missing or extra arguments, creating a really
    simple interface for sending parameters to the tag:
    
        # Handler inside of the MyTag class
        def my_tag(self, context, nodelist, myflag=False):
            content = nodelist.render(context)
            if myflag is True:
                content = "<div class='hidden'>%s</div>" % (content,)
            return content

        # In template:
        {# With optional var specified: #}
        {% mytag myflag=True %} Some content {% endmytag %}

        {# Without option var: #}
        {% mytag %} Other content {% endmytag %}

    Tag handlers support all the fancy stuff: required params, the *args catch-all, and the
    **kwargs catch-all.

    ``intermediate_tags`` is a list of strings that acts as a declaration of all possible
    intermediate tag names that can show up in the body of your main tag.  For example, if you use
    ``intermediate_tags = ["unless"]``, you could write something like this in your templates:
    
        {% mytag myflag=True %}
            some content
        {% unless %}
            secondary content
        {% endmytag %}

    By default, both of these sections are parsed and rendered, but they are handed off to separate
    methods on your tag class for processing, allowing you to dynamically decide if or how to render
    the sibling branches.  In the following example, you a variable is used to toggle which arm of
    the compound tag is rendered:

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

    Because the ``mytag`` handler is always executed first, you can rely on ``self.myflag`` being
    set by the time the ``unless`` handler is called.

    Note that you can have more than one type of intermediate tag, and they can appear in any order,
    and even appear multiple times:
    
        {% mytag %}
            Header content, rendered by the main "mytag" handler
            {% section header="First" %}
                Some content, to be rendered by the "section" handler
            {% section header="Second" is_required=someflag %}
                More content, also rendered by the "section" handler
            {% footer %}
                Content, possibly only rendered if some running calculation is satisfied.
        {% endmytag %}

    """

    name = None
    intermediate_tags = ()
    end_tag = None

    @staticmethod
    def wrap_handler(handler):
        """ Wraps the ``handler`` to resolve template variables automatically. """
        @wraps(handler)
        def wrapper(context, nodelist, *args, **kwargs):
            args = [arg.resolve(context) for arg in args]
            for k, v in kwargs.items():
                kwargs[k] = v.resolve(context)
            return handler(context=context, nodelist=nodelist, *args, **kwargs)
        return wrapper

    @classmethod
    def handler_parser(cls, parser, token, name, handler):
        """
        Returns a wrapped partial of ``handler`` with the arguments supplied by the calling
        template.  Errors will bubble up for invalid or missing arguments to the handler.
        """
        params, varargs, varkw, defaults = getargspec(handler)
        wrapped = cls.wrap_handler(handler)
        params.pop(0)  # removes inspected 'self' from required tag arguments

        special_params = ['context', 'nodelist']  # Rendering params that aren't given by template
        for param in special_params:
            if param in params:
                params.pop(params.index(param))

        bits = token.split_contents()[1:]
        args, kwargs = parse_bits(parser, bits, params, varargs, varkw, defaults, None, name)
        return partial(wrapped, *args, **kwargs)

    @classmethod
    def parser(cls, parser, token):
        """ The compiler function that creates an instance of this Node. """
        if cls.name is None:
            raise ValueError("%r tag should define attribute 'name'" % cls.__name__)

        node = cls()

        # Detect if an end tag or intermediate tags will appear.
        if cls.end_tag:
            parse_until = []
            if cls.intermediate_tags:
                parse_until.extend(list(cls.intermediate_tags))

            if cls.end_tag is True:
                end_tag = "end{}".format(name)
            else:
                end_tag = cls.end_tag
            parse_until.append(end_tag)
        else:
            end_tag = None

        # Get the base handler, named after the tag itself.
        handler = cls.handler_parser(parser, token, cls.name, handler=getattr(node, cls.name))
        current_name = cls.name

        # Parse each nodelist and associate it with the tag piece that came just above it.
        nodelists = []
        stop = len(parse_until) == 0
        while not stop:
            nodelist = parser.parse(parse_until)
            nodelist_name = current_name

            # Fetch the handler for this nodelist
            nodelist_handler = getattr(node, current_name)
            # if isinstance(handler, template.Node):
            #     handler = handler.__init__
            nodelist_handler = cls.handler_parser(parser, token, current_name, nodelist_handler)
            nodelists.append((nodelist_handler, nodelist))

            # Advance the 'current_name' to the newly encountered intermediate tag name
            token = parser.next_token()
            current_name = token.contents.split()[0]

            # If this is the end, remove the end{name} tag from the processing queue.
            if token.contents == end_tag:
                parser.delete_first_token()
                stop = True

        node.nodelists = nodelists
        return node

    @classmethod
    def register_tag(cls, library):
        """ Registers this tag's compiler to the target ``library``. """
        return library.tag(cls.name, cls.parser)

    def __init__(self):
        pass

    def render(self, context):
        """ Calls each handler with its associated nodelist, returning their joined strings. """
        content = []
        for handler, nodelist in self.nodelists:
            content.append(handler(context=context, nodelist=nodelist))
        return u"".join(map(unicode, content))



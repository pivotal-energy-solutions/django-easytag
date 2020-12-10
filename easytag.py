from inspect import getfullargspec

from functools import partial, wraps

from django.template import Node
from django.template.library import parse_bits


class EasyTag(Node):
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
        _data = getfullargspec(handler)
        params, varargs, varkw, defaults, _kwonlyargs, _kwonlydefaults, _annotations = _data
        wrapped = cls.wrap_handler(handler)
        params.pop(0)  # removes inspected 'self' from required tag arguments

        special_params = ['context', 'nodelist']  # Rendering params that aren't given by template
        for param in special_params:
            if param in params:
                params.pop(params.index(param))

        bits = token.split_contents()[1:]
        args, kwargs = parse_bits(parser, bits, params, varargs, varkw,
                                  defaults, (), (), None, name)
        kwargs.update(zip(params, args))
        return partial(wrapped, **kwargs)

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
                end_tag = "end{0}".format(cls.name)
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

            # If this is the end, queue the optional endtoken handler.
            if token.contents == end_tag:
                stop = True
                endtoken_handler = getattr(node, token.contents, None)
                if endtoken_handler:
                    nodelists.append((endtoken_handler, None))

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
            kwargs = {'context': context}
            if nodelist is not None:
                kwargs['nodelist'] = nodelist
            content.append(handler(**kwargs))
        return str("".join(map(str, content)))

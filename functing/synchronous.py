def asTemplate(f):
    def wrapped(*args, **props):
        def execute():
            return f(*args, **props)
        return execute
    return wrapped

def renderProps(**props):
    result = [f' {key}="{value}"' if isinstance(value, str) else f' {key}={str(value)}' for key, value in props.items()]
    return ''.join(result)

def renderChildren(children):
    result = []
    for child in children:
        if callable(child):
            result.extend(child())
        else:
            result.append(child)
    return result

@asTemplate
def Children(*children):
    return renderChildren(children)

def createTag(tagName):
    def propertiesDefinition(**props):
        cache1 = f'<{tagName}{renderProps(**props)}>'
        cache2 = f'</{tagName}>'
        @asTemplate
        def body(*children):
            renderedChildren = renderChildren(children)
            return [cache1, *renderedChildren, cache2]
        return body
    return propertiesDefinition

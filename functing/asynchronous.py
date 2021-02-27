from inspect import isawaitable 
import asyncio

def asTemplate(f):
    def wrapped(*args, **props):
        def execute():
            return f(*args, **props)
        return execute
    return wrapped


async def renderChildren(children):
    results = [*children]
    
    # 1st phase, gather all awaitables
    awaitableIndexes = []
    awaitables = []
    for index, child in enumerate(children):
        if isawaitable(child):
            awaitables.append(child)
            awaitableIndexes.append(index)
        #results[index] = child
            
    # await all and gather results
    awaitedChildren = await asyncio.gather(*awaitables)
    # write results to appropriate place
    for index, child in zip(awaitableIndexes, awaitedChildren):
        results[index] = child
            
    # 2nd phase call callables and detect if there are callable with awaitable results
    calledResults = [*results]
    awaitableIndexes = []
    awaitables = []
    callableIndexes = {-1}
    for index, child in enumerate(results):
        if callable(child):
            callableIndexes.add(index)
            childResult = child()
            calledResults[index] = childResult
            if isawaitable(childResult):
                # awaitable item must be put into a list
                awaitables.append(childResult)
                awaitableIndexes.append(index)
            
    # 3rd phase,
    # await all awaitables (results of callables) and gather results
    awaitedChildren = await asyncio.gather(*awaitables)
    # write results to appropriate place
    for index, child in zip(awaitableIndexes, awaitedChildren):
        calledResults[index] = child
    
    result = []
    for index, child in enumerate(calledResults):
        if index in callableIndexes:
            result.extend(child)
        else:
            result.append(child)
    
    return result
    #return calledResults.values()

@asTemplate
async def Children(*children):
    return await renderChildren(children)

def renderProps(**props):
    result = [f' {key}="{value}"' if isinstance(value, str) else f' {key}={str(value)}' for key, value in props.items()]
    return ''.join(result)

def createTag(tagName):
    def propertiesDefinition(**props):
        cache1 = f'<{tagName}{renderProps(**props)}>'
        cache2 = f'</{tagName}>'
        @asTemplate
        async def body(*children):
            renderedChildren = await renderChildren(children)
            return [cache1, *renderedChildren, cache2]
        return body
    return propertiesDefinition


#
# Fiber
#
# This is a format-independent abstraction for a Fiber that dispatches
# method calls to a format-specific version. The reason this class
# exists is that it lets us define swoop programs first, then fill in
# the formats as a later step (using setImplementation()).
#

class Fiber:
  def __init__(self, name):
    self.implementation = None
    self.name = name
    
  def setImplementation(self, imp):
    self.implementation = imp
    
  def setupSlice(self, base, bound, max_num):
    return self.implementation.setupSlice(base, bound, max_num)
  
  def nextInSlice(self):
    return self.implementation.nextInSlice()
  
  def handleToCoord(self, handle):
    return self.implementation.handleToCoord(handle)
  
  def handleToPayload(self, handle):
    return self.implementation.handleToPayload(handle)
  
  def coordToHandle(self, coord):
    return self.implementation.coordToHandle(coord)
  
  def insertElement(self, coord):
    return self.implementation.insertElement(coord)
  
  def updatePayload(self, handle, payload):
    return self.implementation.updatePayload(handle, payload)

#
# AST
#
# Base Class for all AST nodes
# Currently all AST nodes contain a reference to a Swoop Fiber.
#
class AST:

  def __init__(self, fiber):
    self.fiber = fiber

  def initialize(self):
    pass
    
  def evaluate(self):
    return None
  
  def trace(self, args):
    if (hasattr(self, "fiber") and self.fiber != None):
      print(self.fiber.name + ":", args)
    else:
      print(args)

#
# Slice
#
# Given an AST::Fiber, and a slice spec returns a rank-1 stream of all handles
# to elements in that slice.
# 

class Slice (AST):
  def __init__(self, fiber, base = 0, bound  = None, max_num = None):
    super().__init__(fiber)
    self.base = base
    self.bound = bound
    self.max_num = max_num
  
  
  def initialize(self):
    self.fiber.setupSlice(self.base, self.bound, self.max_num)
  
  def evaluate(self):
    res = self.fiber.nextInSlice()
    self.trace(f"NextInSlice: {res}")
    return res
  
#
# Iterate
#
# Simple convenience alias for iterating over an entire fiber
#

def Iterate(fiber):
  return Slice(fiber)

#
# HandlesToCoords
#
# Given a reference to an AST Fiber, and an AST Node that 
# that produces a 1-stream of handles, produces a 1-stream of coordinates
#
class HandlesToCoords (AST):

  def __init__(self, fiber, handles):
    super().__init__(fiber)
    self.handles = handles

  def initialize(self):
    self.handles.initialize()

  def evaluate(self):
    handle = self.handles.evaluate()
    if handle is None:
      return None
    coord = self.fiber.handleToCoord(handle)
    self.trace(f"HandleToCoord: {handle}, {coord}")
    return coord
    
#
# HandlesToPayloads
#
# Given a reference to an AST Fiber, and an AST Node that 
# that produces a 1-stream of handles, produces a 1-stream of payloads
#
class HandlesToPayloads (AST):

  def __init__(self, fiber, handles):
    super().__init__(fiber)
    self.handles = handles

  def initialize(self):
    self.handles.initialize()

  def evaluate(self):
    handle = self.handles.evaluate()
    if handle is None:
      return None
    payload = self.fiber.handleToPayload(handle)
    self.trace(f"HandleToPayload: {payload}")
    return payload


#
# HandlesToCoordsAndPayloads
#
# Simple convenience alias for concise code
#
#def HandlesToCoordsAndPayloads(fiber, handles):
#  handles2 = Split(handles)
#  return (HandlesToCoords(fiber, handles2), HandlesToPayloads(fiber, handles2))
  


#
# CoordsToHandles
#
# Given a reference to an AST Fiber, and an AST Node that 
# that produces a 1-stream of coords, produces a 1-stream of handles
# (NOTE: EXPENSIVE FOR MOST FORMATS)
# TODO: Add starting position.
#
class CoordsToHandles (AST):

  def __init__(self, fiber, coords):
    super().__init__(fiber)
    self.coords = coords

  def initialize(self):
    self.coords.initialize()
    
  def evaluate(self):
    coord = self.coords.evaluate()
    if coord is None:
      return None
    handle = self.fiber.coordToHandle(coord)
    self.trace(f"CoordToHandle: {coord}, {handle}")
    return handle

#
# InsertElement
#
# Given a reference to an AST Fiber, and an AST Node that 
# that produces a 1-stream of coords, produces a 1-stream of handles
# after creating that (coord, payload) element and initializing coord
# (NOTE: EXPENSIVE FOR MOST FORMATS)
# TODO: Add starting position.
#

class InsertElement (AST):

  def __init__(self, fiber, coords):
    super().__init__(fiber)
    self.coords = coords

  def initialize(self):
    self.coords.initialize()

  def evaluate(self):
    coord = self.coords.evaluate()
    if coord is None:
      return None
    handle = self.fiber.insertElement(coord)
    self.trace(f"InsertElement: {coord}, {handle}")
    return handle

#
# UpdatePayload
#
# Given a reference to an AST Fiber, and an AST Node that produces
# a 1-stream of handles, and an AST Node that produces a 1-stream
# of payloads, updates the element (coord, payload) to the new payload.
#

class UpdatePayload (AST):

  def __init__(self, fiber, handles, payloads):
    super().__init__(fiber)
    self.handles = handles
    self.payloads = payloads

  def initialize(self):
    self.handles.initialize()
    self.payloads.initialize()

  def evaluate(self):
    handle = self.handles.evaluate()
    if handle is None:
      return None
    payload = self.payloads.evaluate()
    if payload is None:
      return None
    self.trace(f"UpdatePayload: {handle}, {payload}")
    return self.fiber.updatePayload(handle, payload)


# 
# Intersect
# 
#

class Intersect (AST):
  def __init__(self, a_coords, a_handles, b_coords, b_handles):
    self.fiber = None
    self.a_coords = a_coords
    self.a_handles = a_handles
    self.b_coords = b_coords
    self.b_handles = b_handles
  
  def initialize(self):
    self.a_coords.initialize()
    self.a_handles.initialize()
    self.b_coords.initialize()
    self.b_handles.initialize()

  def evaluate(self):
    a_coord = self.a_coords.evaluate()
    a_handle = self.a_handles.evaluate()
    b_coord = self.b_coords.evaluate()
    b_handle = self.b_handles.evaluate()
    while a_coord != None and b_coord != None:
      if a_coord == b_coord:
        self.trace(f"Intersection found at: {a_coord}: ({a_handle}, {b_handle})")
        return (a_coord, a_handle, b_handle)
      while a_coord != None and b_coord != None and a_coord < b_coord:
        a_coord = self.a_coords.evaluate()
        a_handle = self.a_handles.evaluate()
        self.trace(f"Intersection advancing A: {a_coord}, {b_coord} ({a_handle}, {b_handle})")
      while b_coord != None and a_coord != None and b_coord < a_coord:
        b_coord = self.b_coords.evaluate()
        b_handle = self.b_handles.evaluate()
        self.trace(f"Intersection advancing B: {a_coord}, {b_coord} ({a_handle}, {b_handle})")
    self.trace("Intersection done.")
    return (None, None, None)
  

#
# FanOut
#
# Given an AST node that produces a 1-stream, fan it out into N 1-streams,
# each with all values from the original stream
#

class FanOut (AST):
  def __init__(self, stream, num):
    self.stream = stream
    self.num = num
    self.cur = 0
  
  def initialize(self):
    if self.cur == 0:
      self.stream.initialize()
    self.cur += 1
    if self.cur == self.num:
      self.cur = 0

  def evaluate(self):
    if self.cur == 0:
      self.result = self.stream.evaluate()
    self.trace(f"Fanout[{self.cur}]: {self.result}")
    self.cur += 1
    if self.cur == self.num:
      self.cur = 0
    return self.result

#
# Split
#
# Given an AST node that produces a 1-stream of tuples, split it into
# the first and second element.
#

class Split (AST):
  def __init__(self, stream, num):
    self.stream = stream
    self.num = num
    self.cur = 0
  
  def initialize(self):
    if self.cur == 0:
      self.stream.initialize()
    self.cur += 1
    if self.cur == self.num:
      self.cur = 0
    
  def evaluate(self):
    if self.cur == 0:
      self.result = self.stream.evaluate()
    res = self.result[self.cur]
    self.trace(f"Split[{self.cur}]: {res}")
    self.cur += 1
    if self.cur == self.num:
      self.cur = 0
    return res

#
# Compute
#
# Given an N-argument, function and a list of N AST nodes that produce
# 1-streams of values, apply the function to the values to produce a 1-stream
# of outputs
#

class Compute (AST):
  def __init__(self, function, *streams):
    self.streams = streams
    self.function = function
  
  def initialize(self):
    for stream in self.streams:
      stream.initialize()
      
  def evaluate(self):
    args = [None] * len(self.streams)
    for x, stream in enumerate(self.streams):
      args[x] = stream.evaluate()
    result = self.function(*args)
    self.trace(f"Compute({args}) => {result}")
    return result


#
# BasicFiberImplementation
#
# Fiber implementation JUST to test out the program below.

class BasicFiberImplementation:
  def __init__(self, vals):
    self.vals = vals
  
  def setupSlice(self, base, bound, max_num):
    # ignore base/bound/max num because this class is BASIC.
    self.max_num = len(self.vals)
    self.cur_num = 0
  
  def nextInSlice(self):
    if self.cur_num >= self.max_num:
      return None
    num = self.cur_num
    self.cur_num += 1
    return num
  
  def handleToCoord(self, handle):
    return handle
  
  def handleToPayload(self, handle):
    return self.vals[handle]
  
  def coordToHandle(self, coord):
    return coord
  
  def insertElement(self, coord):
    return coord
  
  def updatePayload(self, handle, payload):
    if handle != None:
      self.vals[handle] = payload
    return handle


#
# evaluate
#
# Run the given node (and all nodes connected to it) until it returns None
#

def evaluate(node):
  node.initialize()
  res = node.evaluate()
  while (res != None):
    res = node.evaluate()

## Test program: Element-wise multiplication


A = Fiber("A")
B = Fiber("B")
Z = Fiber("Z")

a_handles = Iterate(A)
b_handles = Iterate(B)
a_handles_fanout = FanOut(a_handles, 2)
b_handles_fanout = FanOut(b_handles, 2)
a_coords = HandlesToCoords(A, a_handles_fanout)
b_coords = HandlesToCoords(B, b_handles_fanout)
ab = Intersect(a_coords, a_handles_fanout, b_coords, b_handles_fanout)
ab2 = Split(ab, 3)
z_handles = InsertElement(Z, ab2)
a_values = HandlesToPayloads(A, ab2)
b_values = HandlesToPayloads(B, ab2)
results = Compute(lambda a, b: a*b, a_values, b_values)
final_program = UpdatePayload(Z, z_handles, results)

myA = BasicFiberImplementation([1, 2, 3])
myB = BasicFiberImplementation([4, 5, 6])
myZ = BasicFiberImplementation([None, None, None])

A.setImplementation(myA)
B.setImplementation(myB)
Z.setImplementation(myZ)
evaluate(final_program)
print(myZ.vals)
assert(myZ.vals == [4, 10, 18])

// Define a grammar called Hello
grammar Hello;

import Terminals;

r  : 'hello' ID ;         // match keyword hello followed by an identifier

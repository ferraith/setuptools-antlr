// define a grammar called SomeGrammar
grammar SomeGrammar;

r   : 'hello' ID;
ID  : [a-z]+ ;
WS  : [ \t\r\n]+ -> skip ;

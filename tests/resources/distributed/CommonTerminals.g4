grammar CommonTerminals;

IDENTIFIER
    : ('A'..'Z' | 'a'..'z' | '_') ('A'..'Z' | 'a'..'z' | '0'..'9' | '_')*
    ;

SEPARATOR
    : ','
    ;

WS
    :
    [ \t\r\n]+ -> skip
    ;

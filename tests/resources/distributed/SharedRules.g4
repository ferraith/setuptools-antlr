grammar SharedRules;

import CommonTerminals;

sub_rule_foo
    : 'foo' IDENTIFIER
    ;

sub_rule_bar
    : 'bar' IDENTIFIER (SEPARATOR IDENTIFIER)*
    ;

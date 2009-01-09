reset

set parametric
set style data lines

plot '< python unwrap.py' index 0 u 2:3,\
     '' index 1 u 2:3
#!/usr/bin/perl
# -*- coding:utf-8 -*-

use utf8;
binmode STDIN, ':encoding(utf8)';
binmode STDOUT, ':encoding(utf8)';
use 5.010;
use File::Basename;

my $infile = $ARGV[0];
my $outfile = $ARGV[1];
my $tmpfile = $outfile.".clean";

## 检查文件页数
my $pages = `pdfinfo $infile | grep -Ei '^Pages'`;
$pages =~ s/\D+//g;
exit 0 if $pages > 80;

## PDF转文本
my $command = "pdftotext -nodiag -nopgbrk -q \"".$infile. "\"  ".$tmpfile;
system($command);

open iFH, "<$tmpfile" or die;
open(oFH, ">$outfile") or die;
my $count = 0;
my $toc = 0;
while(<iFH>) {
    $count++;
    chomp;
    next if /^[^a-z]*$/i;  ## 排除非单词行
    $toc = 1 if /^\s*contents\s*$/i;
    if (/^\s*(ACKNOWLEDGMENTS*|references|literatures* +cited)\s*$/i) {
	last if $toc < 1 or $count > 200
    }
    s/[^[:ascii:]]//g;
    print oFH $_.' ';
}
print oFH "\n";

close iFH;
close oFH;
unlink $tmpfile;


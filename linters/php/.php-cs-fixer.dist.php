# codestyle-check (codelint): PHP PHP-CS-Fixer 推荐配置
# 使用方法：拷贝到项目根目录 .php-cs-fixer.dist.php：
#   composer require --dev friendsofphp/php-cs-fixer
#   vendor/bin/php-cs-fixer fix --dry-run   # 检查
#   vendor/bin/php-cs-fixer fix             # 自动修复
# 静态分析另配：composer require --dev phpstan/phpstan && vendor/bin/phpstan analyse

<?php

$finder = (new PhpCsFixer\Finder())
    ->in([__DIR__ . '/src', __DIR__ . '/tests'])
    ->exclude(['vendor']);

return (new PhpCsFixer\Config())
    ->setRules([
        '@PSR12' => true,
        'array_syntax' => ['syntax' => 'short'],
        'ordered_imports' => ['sort_algorithm' => 'alpha'],
        'no_unused_imports' => true,
        'not_operator_with_successor_space' => true,
        'single_quote' => true,
        'trailing_comma_in_multiline' => true,
        'phpdoc_align' => false,
        'yoda_style' => false,
    ])
    ->setFinder($finder)
    ->setHideProgress(false);
